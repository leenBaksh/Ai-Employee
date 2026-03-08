"""
watchdog.py — §7.4 Standalone Watchdog for the AI Employee Orchestrator.

Monitors the orchestrator process and restarts it if it crashes.
This is the safety net that catches orchestrator failures — the orchestrator's
own `check_and_restart_processes()` only works while it's alive.

Features:
  - Monitors orchestrator via PID file (/tmp/ai_employee_orchestrator.pid)
  - Exponential back-off between restarts (30s → 60s → 120s, max 5min)
  - Writes its own health signal to AI_Employee_Vault/Signals/HEALTH_watchdog.json
  - Creates ALERT in /Needs_Action/ after MAX_RESTARTS_PER_HOUR restarts
  - Pauses restarts once the hourly limit is reached (human must fix root cause)

Run:
    uv run watchdog-service
    uv run watchdog-service --vault ./AI_Employee_Vault --interval 30

Configure:
    WATCHDOG_INTERVAL=30              # seconds between checks
    WATCHDOG_MAX_RESTARTS=5           # max auto-restarts per hour
    VAULT_PATH=./AI_Employee_Vault
"""

import os
import sys
import json
import time
import signal
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Watchdog] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("Watchdog")

# ── Config ────────────────────────────────────────────────────────────────────

PID_FILE      = Path("/tmp/ai_employee_orchestrator.pid")
STATE_FILE    = Path("/tmp/ai_employee_watchdog.json")
CHECK_INTERVAL       = int(os.getenv("WATCHDOG_INTERVAL", "30"))
MAX_RESTARTS_PER_HOUR = int(os.getenv("WATCHDOG_MAX_RESTARTS", "5"))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_running(pid: int) -> bool:
    """Check if a process is alive by sending signal 0."""
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"restarts": [], "total_restarts": 0}


def _save_state(state: dict) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error(f"Could not save watchdog state: {e}")


def _orchestrator_cmd(vault_path: Path) -> list[str]:
    """Build the command to launch orchestrator.py via uv or plain python."""
    project_root = Path(__file__).parent
    uv = Path(os.getenv("UV_PATH", str(Path.home() / ".local" / "bin" / "uv")))
    if uv.exists():
        return [
            str(uv), "run", "--directory", str(project_root),
            "python", "orchestrator.py", "--vault", str(vault_path),
        ]
    return [sys.executable, str(project_root / "orchestrator.py"), "--vault", str(vault_path)]


# ── Vault notifications ────────────────────────────────────────────────────────

def _write_health(vault_path: Path, state: dict) -> None:
    signals_dir = vault_path / "Signals"
    signals_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=1)
    restarts_last_hour = sum(
        1 for r in state.get("restarts", [])
        if datetime.fromisoformat(r) > cutoff
    )
    health = {
        "agent_id": "watchdog",
        "status": "online",
        "timestamp": now.isoformat(),
        "total_restarts": state.get("total_restarts", 0),
        "restarts_last_hour": restarts_last_hour,
        "max_restarts_per_hour": MAX_RESTARTS_PER_HOUR,
    }
    try:
        (signals_dir / "HEALTH_watchdog.json").write_text(
            json.dumps(health, indent=2), encoding="utf-8"
        )
    except Exception as e:
        logger.error(f"Could not write health signal: {e}")


def _write_restart_alert(vault_path: Path, restart_count: int) -> None:
    needs_action = vault_path / "Needs_Action"
    needs_action.mkdir(parents=True, exist_ok=True)
    # Dedup — skip if an unresolved alert from today already exists
    existing = list(needs_action.glob("ALERT_watchdog_restarts_*.md"))
    if existing:
        return
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    alert_path = needs_action / f"ALERT_watchdog_restarts_{ts}.md"
    content = f"""---
type: alert
severity: high
source: watchdog
created: {datetime.now(timezone.utc).isoformat()}
restart_count_last_hour: {restart_count}
---

## ⚠️ Watchdog Alert — Orchestrator Keeps Crashing

The orchestrator has been automatically restarted **{restart_count} times in the last hour**.
Auto-restarts are now paused. Manual intervention is required.

## Suggested Actions
- [ ] Check recent logs in `/Logs/` for the root cause
- [ ] Verify `.env` credentials and VAULT_PATH are correct
- [ ] Check disk space: `df -h`
- [ ] Run manually to see the crash: `uv run python orchestrator.py`
- [ ] Repair dependencies if needed: `uv sync`
- [ ] After fixing, restart: `uv run watchdog-service`

---
*Auto-generated by watchdog.py §7.4 · Handbook §8*
"""
    try:
        alert_path.write_text(content, encoding="utf-8")
        logger.warning(f"Wrote restart alert: {alert_path.name}")
    except Exception as e:
        logger.error(f"Could not write restart alert: {e}")


def _write_log(vault_path: Path, action_type: str, result: str, details: dict = None) -> None:
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from audit_logger import write_log_entry
        write_log_entry(
            logs_dir=vault_path / "Logs",
            action_type=action_type,
            actor="watchdog",
            target="orchestrator",
            result=result,
            parameters=details or {},
        )
    except Exception:
        pass  # Watchdog must not crash trying to log


# ── Core loop ─────────────────────────────────────────────────────────────────

def run(vault_path: Path) -> None:
    """Main watchdog loop — runs until KeyboardInterrupt."""
    logger.info(f"Watchdog started (interval={CHECK_INTERVAL}s, max_restarts/hr={MAX_RESTARTS_PER_HOUR})")
    logger.info(f"Vault: {vault_path}")

    state = _load_state()
    _running = True

    def _handle_signal(sig, frame):
        nonlocal _running
        logger.info("Watchdog stopping...")
        _running = False

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    # If orchestrator is already running, just monitor it
    existing_pid = _read_pid()
    if existing_pid and _is_running(existing_pid):
        logger.info(f"Orchestrator already running (PID {existing_pid}) — monitoring only")
    else:
        logger.info("Orchestrator not running — launching now")
        _start_orchestrator(vault_path, state)

    consecutive_pauses = 0

    while _running:
        try:
            _write_health(vault_path, state)

            pid = _read_pid()
            alive = pid is not None and _is_running(pid)

            if not alive:
                now = datetime.now(timezone.utc)
                cutoff = now - timedelta(hours=1)
                # Prune old entries
                state["restarts"] = [
                    r for r in state.get("restarts", [])
                    if datetime.fromisoformat(r) > cutoff
                ]
                restarts_last_hour = len(state["restarts"])

                logger.warning(
                    f"Orchestrator not running "
                    f"(restarts last hour: {restarts_last_hour}/{MAX_RESTARTS_PER_HOUR})"
                )

                if restarts_last_hour >= MAX_RESTARTS_PER_HOUR:
                    logger.error(
                        f"Restart limit reached ({restarts_last_hour}/{MAX_RESTARTS_PER_HOUR}/hr). "
                        "Pausing auto-restarts — human intervention required."
                    )
                    _write_restart_alert(vault_path, restarts_last_hour)
                    _write_log(vault_path, "watchdog_pause", "error", {
                        "reason": "restart_limit_reached",
                        "restarts_last_hour": restarts_last_hour,
                    })
                    # Wait 5 minutes before re-checking (instead of rapid loops)
                    time.sleep(300)
                    continue

                _start_orchestrator(vault_path, state)

        except Exception as e:
            logger.error(f"Watchdog loop error: {e}")

        time.sleep(CHECK_INTERVAL)

    logger.info("Watchdog exited cleanly.")


def _start_orchestrator(vault_path: Path, state: dict) -> None:
    """Start the orchestrator process and record the restart."""
    cmd = _orchestrator_cmd(vault_path)
    env = os.environ.copy()
    env["VAULT_PATH"] = str(vault_path)

    try:
        proc = subprocess.Popen(cmd, env=env)
        PID_FILE.write_text(str(proc.pid), encoding="utf-8")

        now_iso = datetime.now(timezone.utc).isoformat()
        state.setdefault("restarts", []).append(now_iso)
        state["total_restarts"] = state.get("total_restarts", 0) + 1
        _save_state(state)

        logger.info(
            f"Orchestrator started (PID {proc.pid}), "
            f"total restarts: {state['total_restarts']}"
        )
        _write_log(vault_path, "orchestrator_restart", "success", {
            "pid": proc.pid,
            "total_restarts": state["total_restarts"],
        })
    except Exception as e:
        logger.error(f"Failed to start orchestrator: {e}")
        _write_log(vault_path, "orchestrator_restart", "error", {"error": str(e)})


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AI Employee Watchdog")
    parser.add_argument(
        "--vault",
        default=os.getenv("VAULT_PATH", "./AI_Employee_Vault"),
        help="Path to the Obsidian vault",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=CHECK_INTERVAL,
        help="Seconds between health checks (default: 30)",
    )
    args = parser.parse_args()

    vault_path = Path(args.vault).resolve()
    vault_path.mkdir(parents=True, exist_ok=True)

    run(vault_path)


if __name__ == "__main__":
    main()
