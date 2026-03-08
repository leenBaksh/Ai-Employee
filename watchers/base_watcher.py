"""base_watcher.py — Abstract base class for all AI Employee watchers."""

import os
import sys
import time
import logging
import tempfile
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))
from audit_logger import write_log_entry, infer_approval
from retry_handler import classify_error, AuthenticationError, DataError, TransientError

# DEV_MODE / DRY_RUN: default True — safe by default, must explicitly set to "false"
# DEV_MODE takes precedence over DRY_RUN if both are set.
def _resolve_dry_run() -> bool:
    dev_mode = os.getenv("DEV_MODE", "").lower()
    if dev_mode in ("true", "false"):
        return dev_mode == "true"
    return os.getenv("DRY_RUN", "true").lower() == "true"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)


class BaseWatcher(ABC):
    """
    Template for all AI Employee watchers.

    Subclasses implement check_for_updates() and create_action_file()
    to detect events and write them to the Obsidian vault.
    """

    def __init__(self, vault_path: str, check_interval: int = 60):
        self.vault_path = Path(vault_path).resolve()
        self.needs_action = self.vault_path / "Needs_Action"
        self.logs_path = self.vault_path / "Logs"
        self.check_interval = check_interval
        self.dry_run = _resolve_dry_run()
        self.logger = logging.getLogger(self.__class__.__name__)
        if self.dry_run:
            self.logger.warning("DRY RUN mode — no external actions will be taken. Set DRY_RUN=false to enable.")
        self._ensure_dirs()

    # §7.3 — temp fallback dir when vault is locked/unavailable
    _FALLBACK_DIR = Path(tempfile.gettempdir()) / "ai_employee_fallback"

    def _ensure_dirs(self):
        """Make sure required vault directories exist."""
        for folder in [self.needs_action, self.logs_path]:
            folder.mkdir(parents=True, exist_ok=True)

    def _write_to_fallback(self, filename: str, content: str) -> Path:
        """
        §7.3 Graceful Degradation — vault locked / disk full.
        Write an action file to the system temp directory so no events are lost.
        The orchestrator sync loop (or manual `uv run sync-vault`) moves these back
        to /Needs_Action/ when the vault is available again.
        """
        self._FALLBACK_DIR.mkdir(parents=True, exist_ok=True)
        fallback_path = self._FALLBACK_DIR / filename
        fallback_path.write_text(content, encoding="utf-8")
        self.logger.warning(
            f"Vault write failed — wrote to fallback: {fallback_path}. "
            "Run `uv run sync-vault` or fix vault access to process this file."
        )
        return fallback_path

    def _flush_fallback_to_vault(self) -> int:
        """
        Move any files in the temp fallback dir back to /Needs_Action/ now that
        the vault is available. Returns the count of files synced.
        """
        if not self._FALLBACK_DIR.exists():
            return 0
        synced = 0
        for f in self._FALLBACK_DIR.glob("*.md"):
            try:
                dest = self.needs_action / f.name
                dest.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
                f.unlink()
                self.logger.info(f"Flushed fallback file to vault: {f.name}")
                self.log_action("vault_sync", str(dest), "success", {"source": "fallback"})
                synced += 1
            except Exception as e:
                self.logger.error(f"Could not flush {f.name} to vault: {e}")
        return synced

    @abstractmethod
    def check_for_updates(self) -> list:
        """Return a list of new items to process."""

    @abstractmethod
    def create_action_file(self, item) -> Path:
        """Create a .md file in Needs_Action and return its path."""

    def log_action(self, action_type: str, target: str, result: str, details: dict = None):
        """Append a compliant audit log entry via the central audit_logger."""
        approval_status, approved_by = infer_approval(action_type, self.dry_run)
        write_log_entry(
            logs_dir=self.logs_path,
            action_type=action_type,
            actor=self.__class__.__name__,
            target=target,
            result=result,
            parameters=details or {},
            approval_status=approval_status,
            approved_by=approved_by,
        )

    def run(self):
        """Main event loop — runs continuously until interrupted.

        Uses §7.1 error classification + exponential backoff:
          - TransientError  → exponential backoff, alert after 3 consecutive
          - AuthenticationError → write auth alert, pause indefinitely (human must fix)
          - DataError       → quarantine item, short backoff, alert after 3
          - Other           → generic backoff as before
          - Reset counter on any successful poll.
        """
        self.logger.info(f"Starting {self.__class__.__name__} (interval={self.check_interval}s)")
        consecutive_errors = 0
        max_backoff = self.check_interval * 8

        while True:
            try:
                items = self.check_for_updates()
                if consecutive_errors > 0:
                    self.logger.info(f"Recovered after {consecutive_errors} consecutive error(s).")
                    consecutive_errors = 0
                # §7.3 — flush any files queued during vault outage
                self._flush_fallback_to_vault()

                for item in items:
                    try:
                        path = self.create_action_file(item)
                        self.logger.info(f"Created action file: {path.name}")
                        self.log_action("file_created", str(path), "success")
                    except DataError as e:
                        self.logger.error(f"Data error for {item} — quarantining: {e}")
                        self._quarantine_item(item, str(e))
                        self.log_action("file_created", str(item), "data_error", {"error": str(e)})
                    except OSError as e:
                        # §7.3 — vault locked / disk full → write to temp fallback
                        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                        filename = f"FALLBACK_{self.__class__.__name__}_{ts}.md"
                        try:
                            content = f"---\ntype: fallback\nsource: {self.__class__.__name__}\ncreated: {datetime.now(timezone.utc).isoformat()}\noriginal_error: {e}\n---\n\nVault unavailable. Item: {item}\n"
                            self._write_to_fallback(filename, content)
                            self.log_action("file_created", filename, "fallback", {"error": str(e), "item": str(item)})
                        except Exception:
                            self.logger.error(f"Fallback write also failed for {item}: {e}")
                    except Exception as e:
                        self.logger.error(f"Failed to create action file for {item}: {e}")
                        self.log_action("file_created", str(item), "error", {"error": str(e)})
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                self.logger.info(f"{self.__class__.__name__} stopped.")
                break

            except Exception as e:
                classified = classify_error(e)
                consecutive_errors += 1

                # §7.1 AuthenticationError — pause immediately, alert human
                if isinstance(classified, AuthenticationError):
                    self.logger.error(
                        f"Authentication failure in {self.__class__.__name__}: {e}. "
                        "Pausing — credentials must be fixed before this watcher can continue."
                    )
                    self.log_action(
                        "poll_error", self.__class__.__name__, "auth_error",
                        {"error": str(e), "category": "authentication"}
                    )
                    self._write_auth_error_alert(str(e))
                    # Pause indefinitely — watchdog or human must restart
                    while True:
                        time.sleep(300)

                backoff = min(self.check_interval * (2 ** consecutive_errors), max_backoff)
                self.logger.error(
                    f"Error in check_for_updates [{classified.category}] "
                    f"(attempt {consecutive_errors}): {e}. Retrying in {backoff}s."
                )
                self.log_action(
                    "poll_error", self.__class__.__name__, "error",
                    {
                        "error": str(e),
                        "error_category": classified.category,
                        "consecutive_errors": consecutive_errors,
                        "backoff_seconds": backoff,
                    }
                )

                if consecutive_errors >= 3:
                    self._write_repeated_failure_alert(consecutive_errors, str(e))

                time.sleep(backoff)

    def _quarantine_item(self, item, reason: str) -> None:
        """Move a problematic item to /Quarantine/ to isolate data errors (§7.1)."""
        quarantine = self.vault_path / "Quarantine"
        quarantine.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        report = quarantine / f"QUARANTINE_{self.__class__.__name__}_{ts}.md"
        report.write_text(
            f"""---
type: quarantine
source: {self.__class__.__name__}
created: {datetime.now(timezone.utc).isoformat()}
reason: {reason}
---

## Quarantined Item — Data Error

**Source:** {self.__class__.__name__}
**Reason:** {reason}
**Item:** `{item}`

This item was quarantined because it caused a DataError during processing.
Review the item and either fix it or move this file to `/Rejected/`.

---
*Auto-generated by BaseWatcher §7.1 data error handler*
""",
            encoding="utf-8",
        )
        self.logger.warning(f"Quarantined item: {report.name}")

    def _write_auth_error_alert(self, error: str) -> None:
        """Write a high-priority auth alert to /Needs_Action/ (§7.1 AuthenticationError)."""
        existing = list(self.needs_action.glob(f"ALERT_auth_error_{self.__class__.__name__}_*.md"))
        if existing:
            return
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        alert_file = self.needs_action / f"ALERT_auth_error_{self.__class__.__name__}_{ts}.md"
        alert_file.write_text(
            f"""---
type: alert
severity: critical
source: {self.__class__.__name__}
category: authentication
created: {datetime.now(timezone.utc).isoformat()}
---

## 🔐 Authentication Failure — {self.__class__.__name__} Paused

**{self.__class__.__name__}** has stopped due to an authentication error.
It will not retry automatically — credentials must be refreshed first.

**Error:** `{error}`

## Required Actions
- [ ] Refresh the API token / OAuth credentials in `secrets/`
- [ ] Update `.env` if the credential path changed
- [ ] Restart the orchestrator: `uv run python orchestrator.py`

---
*Auto-generated by BaseWatcher §7.1 authentication error handler*
""",
            encoding="utf-8",
        )
        self.logger.warning(f"Wrote auth error alert: {alert_file.name}")

    def _write_repeated_failure_alert(self, count: int, last_error: str):
        """Write an alert file to /Needs_Action/ after 3+ consecutive failures (Handbook §8)."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        alert_file = self.needs_action / f"ALERT_repeated_failure_{self.__class__.__name__}_{ts}.md"
        # Only create if no existing active alert for this watcher
        existing = list(self.needs_action.glob(f"ALERT_repeated_failure_{self.__class__.__name__}_*.md"))
        if existing:
            return
        content = f"""---
type: alert
severity: high
source: {self.__class__.__name__}
created: {datetime.now(timezone.utc).isoformat()}
consecutive_errors: {count}
---

## ⚠️ Repeated Failure Alert — {self.__class__.__name__}

**{self.__class__.__name__}** has failed **{count} consecutive times** and requires attention.

**Last error:** `{last_error}`

## Suggested Actions
- [ ] Check network connectivity and API credentials in `.env`
- [ ] Review recent log entries in `/Logs/`
- [ ] Restart the orchestrator if the issue persists

---
*Auto-generated by BaseWatcher exponential backoff handler · Handbook §8*
"""
        alert_file.write_text(content, encoding="utf-8")
        self.logger.warning(f"Wrote repeated-failure alert: {alert_file.name}")
