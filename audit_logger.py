"""
audit_logger.py — Central Audit Logging for the AI Employee.

Canonical log format (§6.3 compliance):
  {
    "timestamp":       "2026-01-07T10:30:00Z",
    "action_type":     "email_send",
    "actor":           "claude_code",
    "target":          "client@example.com",
    "parameters":      {"subject": "Invoice #123"},
    "approval_status": "approved",      ← NEW: auto | approved | pending | dry_run | n/a
    "approved_by":     "human",         ← NEW: human | system | auto | n/a
    "result":          "success"
  }

All components call write_log_entry() — no duplicate log logic.
Prune logs older than 90 days automatically (runs at most once per day).

Usage:
    from audit_logger import write_log_entry, ApprovalStatus, ApprovedBy

    write_log_entry(
        logs_dir=vault_path / "Logs",
        action_type="email_send",
        actor="email_mcp",
        target="client@example.com",
        result="success",
        parameters={"subject": "Invoice #123"},
        approval_status=ApprovalStatus.APPROVED,
        approved_by=ApprovedBy.HUMAN,
    )
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("audit_logger")

LOG_RETENTION_DAYS = 90

# Sentinel file — prune runs at most once per calendar day
_PRUNE_SENTINEL = ".last_pruned"


# ── Approval status constants ──────────────────────────────────────────────────

class ApprovalStatus:
    """Standardised approval_status values."""
    APPROVED = "approved"   # human moved to /Approved/
    AUTO     = "auto"       # action taken autonomously, no approval required
    PENDING  = "pending"    # action waiting for human approval
    DRY_RUN  = "dry_run"   # DRY_RUN=true — logged but not executed
    NA       = "n/a"        # read-only or informational, approval not applicable


class ApprovedBy:
    """Standardised approved_by values."""
    HUMAN    = "human"      # human explicitly approved (moved file to /Approved/)
    SYSTEM   = "system"     # system rule auto-approved (e.g. heartbeat, read-only)
    AUTO     = "auto"       # no approval path required for this action type
    NA       = "n/a"        # not applicable


# ── Core writer ───────────────────────────────────────────────────────────────

def write_log_entry(
    logs_dir: Path,
    action_type: str,
    actor: str,
    target: str,
    result: str,
    parameters: Optional[dict] = None,
    approval_status: str = ApprovalStatus.AUTO,
    approved_by: str = ApprovedBy.AUTO,
) -> dict:
    """
    Append a compliant log entry to today's YYYY-MM-DD.json file.

    Returns the entry dict that was written.
    Triggers 90-day log pruning at most once per day.
    """
    logs_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)

    entry = {
        "timestamp":       now.isoformat(),
        "action_type":     action_type,
        "actor":           actor,
        "target":          target,
        "parameters":      parameters or {},
        "approval_status": approval_status,
        "approved_by":     approved_by,
        "result":          result,
    }

    log_file = logs_dir / f"{now.strftime('%Y-%m-%d')}.json"
    entries: list = []
    if log_file.exists():
        try:
            entries = json.loads(log_file.read_text(encoding="utf-8"))
            if not isinstance(entries, list):
                entries = []
        except Exception:
            entries = []

    entries.append(entry)
    log_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    # Prune old logs (at most once per day to avoid I/O on every call)
    _maybe_prune(logs_dir)

    return entry


# ── 90-day retention ──────────────────────────────────────────────────────────

def _maybe_prune(logs_dir: Path) -> None:
    """Run prune_old_logs() at most once per calendar day."""
    sentinel = logs_dir / _PRUNE_SENTINEL
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if sentinel.exists() and sentinel.read_text(encoding="utf-8").strip() == today:
        return  # already pruned today

    pruned = prune_old_logs(logs_dir)
    if pruned:
        logger.info(f"Log retention: pruned {pruned} file(s) older than {LOG_RETENTION_DAYS} days.")

    sentinel.write_text(today, encoding="utf-8")


def prune_old_logs(
    logs_dir: Path,
    retention_days: int = LOG_RETENTION_DAYS,
) -> int:
    """
    Delete YYYY-MM-DD.json log files older than retention_days.

    Returns the number of files deleted.
    Skips any file it cannot parse as a date — safety guard against deleting
    non-log files if someone drops an unexpected file in the Logs directory.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    deleted = 0
    for log_file in logs_dir.glob("????-??-??.json"):
        try:
            file_date = datetime.strptime(log_file.stem, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            if file_date < cutoff:
                log_file.unlink()
                deleted += 1
                logger.debug(f"Pruned log file: {log_file.name}")
        except (ValueError, OSError):
            continue
    return deleted


# ── Helper: infer approval context from action type ───────────────────────────

def infer_approval(action_type: str, dry_run: bool = False) -> tuple[str, str]:
    """
    Infer approval_status and approved_by from action_type and dry_run flag.
    Use this when you don't have explicit approval context.

    Returns (approval_status, approved_by).
    """
    if dry_run:
        return ApprovalStatus.DRY_RUN, ApprovedBy.NA

    # Actions triggered by human-approved files
    approved_keywords = (
        "email_send", "invoice_executed", "linkedin_post", "social_post",
        "whatsapp_reply_sent", "email_draft_approved", "calendar_created",
        "slack_sent", "ralph_loop_started",
    )
    if any(kw in action_type for kw in approved_keywords):
        return ApprovalStatus.APPROVED, ApprovedBy.HUMAN

    # Informational / read-only
    read_keywords = (
        "task_detected", "scheduled_trigger", "health_signal",
        "process_start", "cloud_update_merged", "sla_check",
    )
    if any(kw in action_type for kw in read_keywords):
        return ApprovalStatus.NA, ApprovedBy.NA

    # Default: autonomous action, system-decided
    return ApprovalStatus.AUTO, ApprovedBy.SYSTEM


# ── CLI: inspect logs ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os
    import sys

    vault_path = Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()
    logs_dir   = vault_path / "Logs"

    if len(sys.argv) > 1 and sys.argv[1] == "prune":
        n = prune_old_logs(logs_dir)
        print(f"Pruned {n} log file(s) older than {LOG_RETENTION_DAYS} days.")
        sys.exit(0)

    # Show today's log schema compliance summary
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = logs_dir / f"{today}.json"
    if not log_file.exists():
        print(f"No log file for today ({today}).")
        sys.exit(0)

    entries = json.loads(log_file.read_text(encoding="utf-8"))
    required = {"timestamp", "action_type", "actor", "target",
                "parameters", "approval_status", "approved_by", "result"}

    compliant = sum(1 for e in entries if required.issubset(e.keys()))
    missing_fields = [
        (e.get("action_type", "?"), required - e.keys())
        for e in entries if not required.issubset(e.keys())
    ]

    print(f"Log: {log_file.name}  ({len(entries)} entries)")
    print(f"  Schema compliant:   {compliant}/{len(entries)}")
    if missing_fields:
        print("  Non-compliant entries (action_type → missing fields):")
        for at, missing in missing_fields[:10]:
            print(f"    {at}: missing {missing}")
    else:
        print("  ✅ All entries are schema-compliant.")

    # Log files summary
    all_logs = sorted(logs_dir.glob("????-??-??.json"))
    oldest = all_logs[0].stem if all_logs else "—"
    print(f"\nLog retention: {len(all_logs)} files, oldest: {oldest} (keep {LOG_RETENTION_DAYS} days)")
