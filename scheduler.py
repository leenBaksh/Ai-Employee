"""
scheduler.py — Cron-style scheduler for the AI Employee.

Scheduled jobs:
  - Daily 08:00  → Morning briefing (trigger Claude to update Dashboard)
  - Sunday 22:00 → Weekly audit + CEO Briefing generation
  - Every 30 min → Check /Needs_Action for stale items (SLA monitor)

Usage:
    uv run scheduler
    # or run as background process via orchestrator
"""

import os
import sys
import json
import subprocess
import logging
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

try:
    import schedule
    import time
except ImportError:
    print("ERROR: 'schedule' not installed. Run: uv sync")
    raise SystemExit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Scheduler] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("Scheduler")

VAULT_PATH = Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()
LOGS_DIR = VAULT_PATH / "Logs"
BRIEFINGS_DIR = VAULT_PATH / "Briefings"
NEEDS_ACTION = VAULT_PATH / "Needs_Action"
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

DAILY_BRIEFING_TIME = os.getenv("DAILY_BRIEFING_TIME", "08:00")
WEEKLY_AUDIT_TIME   = os.getenv("WEEKLY_AUDIT_TIME", "22:00")
WEEKLY_AUDIT_DAY    = int(os.getenv("WEEKLY_AUDIT_DAY", "6"))  # 6 = Sunday

WHATSAPP_DAILY_REPORT_ENABLED = os.getenv("WHATSAPP_DAILY_REPORT_ENABLED", "false").lower() == "true"
WHATSAPP_DAILY_REPORT_TIME    = os.getenv("WHATSAPP_DAILY_REPORT_TIME", "08:00")
WHATSAPP_DAILY_REPORT_TO      = os.getenv("WHATSAPP_DAILY_REPORT_TO", "")
WHATSAPP_ACCESS_TOKEN         = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID      = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")


def _log(action_type: str, result: str, details: dict = None):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action_type": action_type,
        "actor": "scheduler",
        "target": "scheduled_job",
        "parameters": details or {},
        "result": result,
    }
    entries = []
    if log_file.exists():
        try:
            entries = json.loads(log_file.read_text(encoding='utf-8'))
        except Exception:
            entries = []
    entries.append(entry)
    log_file.write_text(json.dumps(entries, indent=2), encoding='utf-8')


def _trigger_claude_skill(skill_prompt: str, job_name: str):
    """
    Trigger Claude Code to run a skill.
    Writes a trigger file to /Scheduled/ so the orchestrator picks it up.
    """
    SCHEDULED_DIR = VAULT_PATH / "Scheduled"
    SCHEDULED_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    trigger_file = SCHEDULED_DIR / f"TRIGGER_{timestamp}_{job_name}.md"
    trigger_file.write_text(
        f"""---
type: scheduled_trigger
job: {job_name}
created: {datetime.now(timezone.utc).isoformat()}
status: pending
---

## Scheduled Job: {job_name}

{skill_prompt}

---
*Created automatically by Scheduler*
""",
        encoding='utf-8',
    )
    logger.info(f"Trigger created: {trigger_file.name}")
    _log("scheduled_trigger_created", "success", {"job": job_name, "file": trigger_file.name})


# ── Job Definitions ───────────────────────────────────────────────────────────

def job_daily_briefing():
    """Run every morning — update Dashboard and check inbox."""
    logger.info("▶ Daily briefing job starting")
    if DRY_RUN:
        logger.info("[DRY RUN] Would trigger daily briefing")
        return
    _trigger_claude_skill(
        skill_prompt=(
            "Run the daily morning briefing:\n"
            "1. Read Company_Handbook.md\n"
            "2. Review all files in /Needs_Action/\n"
            "3. Check /Pending_Approval/ for expired items\n"
            "4. Update Dashboard.md with current counts\n"
            "5. Flag any SLA breaches (emails > 24hr old)\n"
            "6. Log all findings"
        ),
        job_name="daily_briefing"
    )
    _log("daily_briefing_triggered", "success")


def job_weekly_audit():
    """Run every Sunday night — generate CEO briefing."""
    logger.info("▶ Weekly audit job starting")
    if DRY_RUN:
        logger.info("[DRY RUN] Would trigger weekly audit")
        return

    today = datetime.now(timezone.utc)
    period_end = today.strftime("%Y-%m-%d")
    period_start = (today - timedelta(days=7)).strftime("%Y-%m-%d")

    _trigger_claude_skill(
        skill_prompt=(
            f"Run the weekly CEO briefing audit for period {period_start} to {period_end}:\n"
            "1. Read Business_Goals.md for targets\n"
            "2. Count completed tasks in /Done/ from this week\n"
            "3. Read Accounting/Current_Month.md for revenue\n"
            "4. Check /Logs/ for all actions this week\n"
            "5. Identify bottlenecks (tasks that took > 2 days)\n"
            "6. Flag unused subscriptions per Business_Goals.md audit rules\n"
            f"7. Write Monday Morning CEO Briefing to /Briefings/{today.strftime('%Y-%m-%d')}_Monday_Briefing.md\n"
            "8. Update Dashboard.md with weekly summary"
        ),
        job_name="weekly_audit"
    )
    _log("weekly_audit_triggered", "success", {"period": f"{period_start} to {period_end}"})


def job_sla_monitor():
    """Every 30 min — check for SLA breaches on pending emails."""
    logger.info("▶ SLA monitor check")
    overdue = []

    for task_file in NEEDS_ACTION.glob("EMAIL_*.md"):
        try:
            content = task_file.read_text(encoding='utf-8')
            # Find 'received:' in frontmatter
            for line in content.split("\n"):
                if line.startswith("received:"):
                    received_str = line.replace("received:", "").strip()
                    received_dt = datetime.fromisoformat(received_str)
                    age_hours = (datetime.now(timezone.utc) - received_dt).total_seconds() / 3600
                    if age_hours > 24:
                        overdue.append({"file": task_file.name, "age_hours": round(age_hours, 1)})
                    break
        except Exception:
            pass

    if overdue:
        logger.warning(f"SLA breaches detected: {len(overdue)} email(s) overdue")
        for item in overdue:
            alert_name = f"ALERT_sla_{item['file']}"
            alert_file = NEEDS_ACTION / alert_name
            # Also skip if ANY existing alert mentions this file (avoids duplicates with Claude-created alerts)
            existing_alerts = list(NEEDS_ACTION.glob("ALERT_*.md"))
            already_alerted = any(
                item['file'].replace('.md', '') in f.stem for f in existing_alerts
            )
            if not alert_file.exists() and not already_alerted:
                alert_file.write_text(
                    f"""---
type: alert
severity: high
created: {datetime.now(timezone.utc).isoformat()}
status: pending
---

SLA Breach: {item['file']}

Email task is **{item['age_hours']} hours old** (SLA = 24 hours).

**Action required:** Review and respond to the client.

Related: [{item['file']}]({item['file']})
""",
                    encoding='utf-8',
                )
        _log("sla_monitor", "breach_detected", {"overdue_count": len(overdue), "items": overdue})
    else:
        logger.info("SLA monitor: all emails within 24hr SLA")


def job_approval_check():
    """Every 30 min — flag expired approval requests."""
    pending_dir = VAULT_PATH / "Pending_Approval"
    if not pending_dir.exists():
        return

    for f in pending_dir.glob("*.md"):
        try:
            content = f.read_text(encoding='utf-8')
            for line in content.split("\n"):
                if line.startswith("expires:"):
                    exp_str = line.replace("expires:", "").strip()
                    exp_dt = datetime.fromisoformat(exp_str)
                    if datetime.now(timezone.utc) > exp_dt:
                        # Already flagged? Also check for Claude-created alerts mentioning this file
                        alert_path = NEEDS_ACTION / f"ALERT_expired_{f.name}"
                        existing_alerts = list(NEEDS_ACTION.glob("ALERT_*.md"))
                        already_alerted = any(
                            f.stem.replace('.md', '') in alert.stem for alert in existing_alerts
                        )
                        if not alert_path.exists() and not already_alerted:
                            alert_path.write_text(
                                f"""---
type: alert
severity: high
created: {datetime.now(timezone.utc).isoformat()}
status: pending
---

Approval Request EXPIRED: {f.name}

The approval window has closed. **Re-approve or reject** this request.

Related file: [Pending_Approval/{f.name}](../Pending_Approval/{f.name})
""",
                                encoding='utf-8',
                            )
                            logger.warning(f"Expired approval flagged: {f.name}")
                            _log("approval_expired_flagged", "success", {"file": f.name})
                    break
        except Exception:
            pass


# ── Gold Tier Jobs ─────────────────────────────────────────────────────────────

def job_odoo_health_check():
    """Daily 09:00 — trigger Claude to verify Odoo connection."""
    logger.info("▶ Odoo health check job starting")
    if DRY_RUN:
        logger.info("[DRY RUN] Would trigger Odoo health check")
        return
    _trigger_claude_skill(
        skill_prompt=(
            "Run the Odoo health check:\n"
            "1. Read Company_Handbook.md\n"
            "2. Use odoo MCP tool `odoo_get_customers` with limit=1 to verify connectivity\n"
            "3. If successful: log result to /Logs/ and update Dashboard.md\n"
            "4. If failed: create /Needs_Action/ALERT_odoo_down.md with error details\n"
            "5. Run `/odoo-health-check` skill for full check"
        ),
        job_name="odoo_health_check"
    )
    _log("odoo_health_check_triggered", "success")


def job_weekly_business_audit():
    """Monday 06:00 — full business audit using Audit MCP."""
    logger.info("▶ Weekly business audit job starting")
    if DRY_RUN:
        logger.info("[DRY RUN] Would trigger weekly business audit")
        return

    today = datetime.now(timezone.utc)
    period_end = today.strftime("%Y-%m-%d")
    period_start = (today - timedelta(days=7)).strftime("%Y-%m-%d")

    _trigger_claude_skill(
        skill_prompt=(
            f"Run the full weekly business audit for {period_start} to {period_end}:\n"
            "1. Read Company_Handbook.md and Business_Goals.md\n"
            "2. Use audit MCP `audit_get_weekly_report` for activity summary\n"
            "3. Use audit MCP `audit_get_errors` to surface errors from the week\n"
            "4. Use odoo MCP `odoo_get_revenue_summary` for financial data\n"
            "5. Check vault health: /Needs_Action, /Pending_Approval, /Done counts\n"
            "6. Identify and flag recurring errors (> 3 occurrences)\n"
            f"7. Write audit report to /Logs/AUDIT_{period_end}.md\n"
            "8. Update Dashboard.md with audit findings\n"
            "9. Run `/weekly-business-audit` skill"
        ),
        job_name="weekly_business_audit"
    )
    _log("weekly_business_audit_triggered", "success", {"period": f"{period_start} to {period_end}"})


def job_social_limits_check():
    """Every 60 min — log remaining social media post slots."""
    logger.info("▶ Social limits check")
    platforms = {
        "Facebook":  int(os.getenv("FACEBOOK_MAX_POSTS_PER_DAY", "2")),
        "Instagram": int(os.getenv("INSTAGRAM_MAX_POSTS_PER_DAY", "2")),
        "Twitter":   int(os.getenv("TWITTER_MAX_POSTS_PER_DAY", "5")),
    }
    # Count posts queued today by checking /To_Post/<Platform>/
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    report = {}
    for platform, limit in platforms.items():
        platform_dir = VAULT_PATH / "To_Post" / platform
        if platform_dir.exists():
            today_posts = [f for f in platform_dir.glob("POST_*.md") if today_str in f.name]
            report[platform] = {"queued": len(today_posts), "limit": limit, "remaining": max(0, limit - len(today_posts))}
        else:
            report[platform] = {"queued": 0, "limit": limit, "remaining": limit}
    logger.info(f"Social limits: {report}")
    _log("social_limits_check", "success", {"limits": report})


def job_daily_whatsapp_report():
    """Daily at configured time — send vault summary to World Digital via WhatsApp."""
    logger.info("▶ Daily WhatsApp report job starting")
    if DRY_RUN:
        logger.info("[DRY RUN] Would send daily WhatsApp report")
        return
    if not WHATSAPP_DAILY_REPORT_TO:
        logger.warning("Daily WhatsApp report skipped — WHATSAPP_DAILY_REPORT_TO not set")
        return
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.warning("Daily WhatsApp report skipped — WhatsApp credentials not set")
        return

    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    # Vault stats
    needs_action = len([f for f in NEEDS_ACTION.glob("*.md") if f.is_file()])
    pending_approval = len(list((VAULT_PATH / "Pending_Approval").glob("*.md")))
    done_total = len(list((VAULT_PATH / "Done").glob("*.md")))

    # Today's action count from log
    log_file = LOGS_DIR / f"{today}.json"
    actions_today = 0
    if log_file.exists():
        try:
            entries = json.loads(log_file.read_text(encoding="utf-8"))
            actions_today = len(entries)
        except Exception:
            pass

    # Status line
    if needs_action == 0 and pending_approval == 0:
        status_line = "✅ All clear — nothing needs your attention."
    else:
        parts = []
        if needs_action > 0:
            parts.append(f"⚠️ {needs_action} task(s) need attention")
        if pending_approval > 0:
            parts.append(f"📋 {pending_approval} approval(s) waiting")
        status_line = " · ".join(parts)

    message = (
        f"🤖 *AI Employee Daily Report*\n"
        f"📅 {now.strftime('%A, %b %d %Y')} — {now.strftime('%H:%M')} UTC\n\n"
        f"📥 Inbox: {needs_action} pending\n"
        f"⏳ Awaiting approval: {pending_approval}\n"
        f"✅ Completed (all time): {done_total}\n"
        f"⚡ Actions logged today: {actions_today}\n\n"
        f"{status_line}\n\n"
        f"_Reply *URGENT* to flag a priority item._\n"
        f"_AI Employee v0.4 Platinum_"
    )

    url = f"https://graph.facebook.com/v25.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = json.dumps({
        "messaging_product": "whatsapp",
        "to": WHATSAPP_DAILY_REPORT_TO,
        "type": "text",
        "text": {"body": message},
    }).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            msg_id = result.get("messages", [{}])[0].get("id", "unknown")
            logger.info(f"Daily WhatsApp report sent to {WHATSAPP_DAILY_REPORT_TO} (msg_id={msg_id})")
            _log("whatsapp_daily_report_sent", "success", {
                "to": WHATSAPP_DAILY_REPORT_TO,
                "msg_id": msg_id,
                "needs_action": needs_action,
                "pending_approval": pending_approval,
                "done_total": done_total,
                "actions_today": actions_today,
            })
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        logger.error(f"Daily WhatsApp report failed (HTTP {e.code}): {body}")
        _log("whatsapp_daily_report_sent", "error", {"error": body})
    except Exception as exc:
        logger.error(f"Daily WhatsApp report error: {exc}")
        _log("whatsapp_daily_report_sent", "error", {"error": str(exc)})


def main():
    logger.info(f"Scheduler starting — vault: {VAULT_PATH}")
    logger.info(f"Daily briefing: {DAILY_BRIEFING_TIME}")
    logger.info(f"Weekly audit: Sunday {WEEKLY_AUDIT_TIME}")
    if DRY_RUN:
        logger.warning("DRY RUN MODE — no external triggers")

    # Daily jobs
    schedule.every().day.at(DAILY_BRIEFING_TIME).do(job_daily_briefing)
    schedule.every().day.at("09:00").do(job_odoo_health_check)  # Gold Tier

    # Daily WhatsApp report (Platinum)
    if WHATSAPP_DAILY_REPORT_ENABLED:
        schedule.every().day.at(WHATSAPP_DAILY_REPORT_TIME).do(job_daily_whatsapp_report)
        logger.info(f"Daily WhatsApp report: {WHATSAPP_DAILY_REPORT_TIME} UTC → {WHATSAPP_DAILY_REPORT_TO}")

    # Weekly audit — Sunday (Silver)
    day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    getattr(schedule.every(), day_names[WEEKLY_AUDIT_DAY]).at(WEEKLY_AUDIT_TIME).do(job_weekly_audit)

    # Weekly business audit — Monday 06:00 (Gold Tier)
    schedule.every().monday.at("06:00").do(job_weekly_business_audit)

    # Continuous monitoring every 30 minutes
    schedule.every(30).minutes.do(job_sla_monitor)
    schedule.every(30).minutes.do(job_approval_check)

    # Social limits check — every 60 minutes (Gold Tier)
    schedule.every(60).minutes.do(job_social_limits_check)

    # Run monitors immediately on startup
    job_sla_monitor()
    job_approval_check()
    job_social_limits_check()  # Gold Tier startup check

    logger.info("Scheduler running. Press Ctrl+C to stop.")
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Scheduler stopped.")
            break
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            _log("scheduler_error", "error", {"error": str(e)})


if __name__ == "__main__":
    main()
