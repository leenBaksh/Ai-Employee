"""
dashboard_server.py — Live web dashboard for the AI Employee Vault.

Serves a real-time browser dashboard at http://localhost:8888/
with vault stats, agent health, task queue, and recent activity logs.

Endpoints:
  GET /               → Renders templates/dashboard.html
  GET /api/stats      → Vault folder counts
  GET /api/health     → Agent health signals
  GET /api/tasks      → Needs_Action/ task list
  GET /api/approvals  → Pending_Approval/ list
  GET /api/logs       → Last 20 log entries
  GET /api/stream     → SSE stream (full dashboard JSON every 5s)

Run:
  uv run dashboard
  uv run python dashboard_server.py
"""

import os
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

from flask import Flask, render_template, jsonify, Response, stream_with_context
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

VAULT_PATH = Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8888"))
HEALTH_OFFLINE_THRESHOLD = int(os.getenv("HEALTH_OFFLINE_THRESHOLD", "300"))  # 5 minutes

app = Flask(__name__)


# ── Data helpers ───────────────────────────────────────────────────────────────

def get_vault_stats() -> dict:
    """Count files in each key vault folder."""
    def count(folder: str, pattern: str = "*.md") -> int:
        d = VAULT_PATH / folder
        return len(list(d.glob(pattern))) if d.exists() else 0

    return {
        "needs_action":       count("Needs_Action"),
        "pending_approval":   count("Pending_Approval"),
        "done":               count("Done", "*"),
        "drafts":             count("Drafts"),
        "scheduled":          count("Scheduled"),
        "in_progress_local":  count("In_Progress/local"),
        "in_progress_cloud":  count("In_Progress/cloud"),
        "sla_breaches":       _count_sla_breaches(),
    }


def _count_sla_breaches() -> int:
    """Count ALERT_sla_* files in Needs_Action."""
    d = VAULT_PATH / "Needs_Action"
    if not d.exists():
        return 0
    return len(list(d.glob("ALERT_sla_*")))


def get_agent_health() -> list:
    """Read health signal files from Signals/."""
    signals_dir = VAULT_PATH / "Signals"
    results = []
    for agent_id in ["local-01", "cloud-01"]:
        signal_file = signals_dir / f"HEALTH_{agent_id}.json"
        entry = {"agent_id": agent_id, "status": "never_seen", "timestamp": None}
        if signal_file.exists():
            try:
                data = json.loads(signal_file.read_text(encoding="utf-8"))
                ts = data.get("timestamp")
                if ts:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    age_seconds = (datetime.now(timezone.utc) - dt).total_seconds()
                    status = "online" if age_seconds <= HEALTH_OFFLINE_THRESHOLD else "offline"
                else:
                    status = "offline"
                entry.update({
                    "status": status,
                    "timestamp": ts,
                    "agent_id": data.get("agent_id", agent_id),
                    "role": data.get("role", "unknown"),
                    "needs_action_count": data.get("needs_action_count", 0),
                    "pending_approval_count": data.get("pending_approval_count", 0),
                    "vault_path": data.get("vault_path", ""),
                })
            except Exception:
                entry["status"] = "error"
        results.append(entry)
    return results


def get_task_list(folder: str = "Needs_Action", limit: int = 20) -> list:
    """List .md files in a vault folder with age metadata."""
    d = VAULT_PATH / folder
    if not d.exists():
        return []
    now = time.time()
    files = []
    for f in sorted(d.glob("*.md"), key=lambda p: p.stat().st_mtime):
        age_seconds = now - f.stat().st_mtime
        files.append({
            "filename": f.name,
            "age_seconds": int(age_seconds),
            "age_human": _human_age(age_seconds),
            "type": _infer_type(f.name),
        })
    return files[:limit]


def _human_age(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds / 60)}m"
    if seconds < 86400:
        return f"{int(seconds / 3600)}h"
    return f"{int(seconds / 86400)}d"


def _infer_type(filename: str) -> str:
    name_lower = filename.lower()
    if name_lower.startswith("alert_sla"):
        return "sla_breach"
    if name_lower.startswith("email_"):
        return "email"
    if name_lower.startswith("whatsapp_"):
        return "whatsapp"
    if name_lower.startswith("invoice_") or name_lower.startswith("inv_"):
        return "invoice"
    if name_lower.startswith("trigger_"):
        return "scheduled"
    if name_lower.startswith("approval_"):
        return "approval"
    if name_lower.startswith("social_") or name_lower.startswith("post_"):
        return "social"
    return "task"


def get_recent_logs(limit: int = 20) -> list:
    """Load the most recent log entries from today's and yesterday's log files."""
    logs_dir = VAULT_PATH / "Logs"
    if not logs_dir.exists():
        return []
    today = datetime.now(timezone.utc)
    dates_to_check = [
        today.strftime("%Y-%m-%d"),
        (today - timedelta(days=1)).strftime("%Y-%m-%d"),
    ]
    entries = []
    for date_str in dates_to_check:
        log_file = logs_dir / f"{date_str}.json"
        if log_file.exists():
            try:
                raw = json.loads(log_file.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    entries.extend(raw)
            except Exception:
                pass
    entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return entries[:limit]


def get_full_dashboard() -> dict:
    """Combine all data into a single dashboard payload."""
    return {
        "stats":        get_vault_stats(),
        "health":       get_agent_health(),
        "tasks":        get_task_list("Needs_Action"),
        "approvals":    get_task_list("Pending_Approval"),
        "logs":         get_recent_logs(20),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/stats")
def api_stats():
    return jsonify(get_vault_stats())


@app.route("/api/health")
def api_health():
    return jsonify(get_agent_health())


@app.route("/api/tasks")
def api_tasks():
    return jsonify(get_task_list("Needs_Action"))


@app.route("/api/approvals")
def api_approvals():
    return jsonify(get_task_list("Pending_Approval"))


@app.route("/api/logs")
def api_logs():
    return jsonify(get_recent_logs(20))


@app.route("/api/stream")
def api_stream():
    """SSE stream — pushes full dashboard JSON every 5 seconds."""
    def generate():
        while True:
            data = json.dumps(get_full_dashboard())
            yield f"data: {data}\n\n"
            time.sleep(5)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    print(f"AI Employee Dashboard → http://localhost:{DASHBOARD_PORT}")
    print(f"Vault: {VAULT_PATH}")
    print("Press Ctrl+C to stop.\n")

    app.run(
        host="0.0.0.0",
        port=DASHBOARD_PORT,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


if __name__ == "__main__":
    main()
