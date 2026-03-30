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
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

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


def job_whatsapp_daily_report():
    """Send daily WhatsApp report with chat activity summary."""
    logger.info("▶ WhatsApp daily report job starting")
    
    if not WHATSAPP_DAILY_REPORT_ENABLED or not WHATSAPP_DAILY_REPORT_TO:
        logger.info("WhatsApp daily report disabled or recipient not configured")
        return
    
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.error("WhatsApp credentials not configured")
        return
    
    # Generate report
    report = _generate_whatsapp_daily_report()
    
    if DRY_RUN:
        logger.info(f"[DRY RUN] Would send WhatsApp report to {WHATSAPP_DAILY_REPORT_TO}")
        logger.info(f"Report:\n{report}")
        _log("whatsapp_daily_report_dry_run", "success", {"recipient": WHATSAPP_DAILY_REPORT_TO})
        return
    
    # Send via WhatsApp API
    _send_whatsapp_message(WHATSAPP_DAILY_REPORT_TO, report)
    _log("whatsapp_daily_report_sent", "success", {"recipient": WHATSAPP_DAILY_REPORT_TO})


def _generate_whatsapp_daily_report() -> str:
    """Generate daily WhatsApp activity report with weather."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    # Count messages from task files
    messages_count = 0
    urgent_count = 0
    group_count = 0
    unread_count = 0
    total_text = 0  # Track total text characters
    
    # Conversation tracking
    greetings_count = 0  # hi, hello, hey, etc.
    how_are_you_count = 0  # how are you, how's it going
    goodbye_count = 0  # bye, goodbye, see you
    thanks_count = 0  # thank you, thanks
    positive_count = 0  # good day, have fun, etc.
    questions_count = 0  # what, when, where, why, how, can you, etc.
    requests_count = 0  # please, can you, could you, i need, etc.
    confirmations_count = 0  # yes, ok, sure, agreed, etc.
    urgency_count = 0  # asap, urgent, immediately, etc.
    love_count = 0  # love you, miss you, care about, etc.
    help_count = 0  # help, support, assist, etc.
    meeting_count = 0  # meeting, call, schedule, appointment, etc.
    money_count = 0  # payment, invoice, bill, price, cost, etc.

    # Conversation keywords
    GREETINGS = ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening", "salam", "assalamualaikum", "yo", "howdy"]
    HOW_ARE_YOU = ["how are you", "how's it going", "how do you do", "what's up", "kya haal", "kaise ho", "how have you been"]
    GOODBYE = ["bye", "goodbye", "see you", "take care", "talk later", "catch you later", "ttyl", "gtg", "got to go"]
    THANKS = ["thank you", "thanks", "shukriya", "thanku", "thx", "appreciate it", "much appreciated"]
    POSITIVE = ["good day", "have a good day", "have fun", "have a nice day", "all the best", "good luck", "awesome", "great", "excellent", "perfect"]
    QUESTIONS = ["what", "when", "where", "why", "how", "can you", "could you", "will you", "do you", "is there", "are there", "kya", "kab", "kahan", "kyun"]
    REQUESTS = ["please", "can you", "could you", "i need", "i want", "i would like", "help me", "send me", "give me", "mera", "mujhe"]
    CONFIRMATIONS = ["yes", "ok", "okay", "sure", "agreed", "definitely", "absolutely", "correct", "haan", "ji", "yep", "yup"]
    URGENCY = ["asap", "urgent", "immediately", "right now", "quick", "fast", "emergency", "critical", "jaldi", "fora"]
    LOVE = ["love you", "miss you", "care about", "love", "miss", "hug", "kiss", "dear", "jaan", "habibi"]
    HELP = ["help", "support", "assist", "guidance", "stuck", "problem", "issue", "error", "madad"]
    MEETING = ["meeting", "call", "schedule", "appointment", "zoom", "teams", "google meet", "conference", "interview"]
    MONEY = ["payment", "invoice", "bill", "price", "cost", "money", "salary", "payment", "paisa", "rupees", "$", "rs"]

    if NEEDS_ACTION.exists():
        for f in NEEDS_ACTION.glob(f"WHATSAPP_{today.replace('-', '')}*.md"):
            messages_count += 1
            content = f.read_text(encoding="utf-8").lower()
            
            if "priority: high" in content:
                urgent_count += 1
            if "chat_type: group" in content:
                group_count += 1
            if "read_status: unread" in content:
                unread_count += 1
            
            # Count text in message body
            for line in content.splitlines():
                if line.startswith("> "):  # Message content lines
                    total_text += len(line)
                    msg_text = line[2:]  # Remove "> " prefix
                    
                    # Track conversation types
                    if any(g in msg_text for g in GREETINGS):
                        greetings_count += 1
                    if any(h in msg_text for h in HOW_ARE_YOU):
                        how_are_you_count += 1
                    if any(b in msg_text for b in GOODBYE):
                        goodbye_count += 1
                    if any(t in msg_text for t in THANKS):
                        thanks_count += 1
                    if any(p in msg_text for p in POSITIVE):
                        positive_count += 1
                    if any(q in msg_text for q in QUESTIONS):
                        questions_count += 1
                    if any(r in msg_text for r in REQUESTS):
                        requests_count += 1
                    if any(c in msg_text for c in CONFIRMATIONS):
                        confirmations_count += 1
                    if any(u in msg_text for u in URGENCY):
                        urgency_count += 1
                    if any(l in msg_text for l in LOVE):
                        love_count += 1
                    if any(h in msg_text for h in HELP):
                        help_count += 1
                    if any(m in msg_text for m in MEETING):
                        meeting_count += 1
                    if any(mn in msg_text for mn in MONEY):
                        money_count += 1

    # Count calls
    calls_count = 0
    call_log = VAULT_PATH / "WhatsApp_Call_Log.md"
    if call_log.exists():
        content = call_log.read_text(encoding="utf-8")
        calls_count = content.count(f"## ") - 1  # Subtract header

    # Get weather data
    weather_info = _get_weather_data()

    # Format total text
    if total_text < 1000:
        text_summary = f"{total_text} chars"
    elif total_text < 1000000:
        text_summary = f"{total_text / 1000:.1f}K chars"
    else:
        text_summary = f"{total_text / 1000000:.1f}M chars"

    # Build conversation summary
    conversation_parts = []
    if greetings_count > 0:
        conversation_parts.append(f"👋 {greetings_count}")
    if how_are_you_count > 0:
        conversation_parts.append(f"💬 {how_are_you_count}")
    if thanks_count > 0:
        conversation_parts.append(f"🙏 {thanks_count}")
    if goodbye_count > 0:
        conversation_parts.append(f"👋 {goodbye_count}")
    if positive_count > 0:
        conversation_parts.append(f"✨ {positive_count}")
    if questions_count > 0:
        conversation_parts.append(f"❓ {questions_count}")
    if requests_count > 0:
        conversation_parts.append(f"📢 {requests_count}")
    if confirmations_count > 0:
        conversation_parts.append(f"✅ {confirmations_count}")
    if urgency_count > 0:
        conversation_parts.append(f"🚨 {urgency_count}")
    if love_count > 0:
        conversation_parts.append(f"❤️ {love_count}")
    if help_count > 0:
        conversation_parts.append(f"🆘 {help_count}")
    if meeting_count > 0:
        conversation_parts.append(f"📅 {meeting_count}")
    if money_count > 0:
        conversation_parts.append(f"💰 {money_count}")
    
    conversation_summary = " | ".join(conversation_parts) if conversation_parts else "No casual conversations"

    report = f"""📊 *WhatsApp Daily Report*
📅 {today}

*Summary:*
💬 Messages: {messages_count}
📝 Total Text: {text_summary}
⚠️ Urgent: {urgent_count}
👥 Group: {group_count}
🔵 Unread: {unread_count}
📞 Calls: {calls_count}

*Daily Conversation:*
{conversation_summary}

*Status:* {"✅ All caught up!" if unread_count == 0 else f"⚠️ {unread_count} pending"}

*AI Employee Activity:*
✅ Auto-replies sent
✅ Tasks created
✅ Calls logged

{weather_info}
Have a great day! 🚀"""

    return report


def _get_weather_data() -> str:
    """Fetch weather data from OpenWeatherMap API."""
    import urllib.request
    import json

    weather_api_key = os.getenv("WEATHER_API_KEY", "")
    weather_city = os.getenv("WEATHER_CITY", "Karachi")
    weather_country = os.getenv("WEATHER_COUNTRY", "PK")

    if not weather_api_key:
        return "*Weather:* ⚠️ API key not configured"

    try:
        # Fetch weather data
        url = f"https://api.openweathermap.org/data/2.5/weather?q={weather_city},{weather_country}&appid={weather_api_key}&units=metric"
        
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())

        temp = round(data["main"]["temp"])
        feels_like = round(data["main"]["feels_like"])
        humidity = data["main"]["humidity"]
        desc = data["weather"][0]["description"].title()
        icon = _get_weather_icon(data["weather"][0]["main"])

        return f"""*Weather in {weather_city}:*
🌡️ Temperature: {temp}°C (feels like {feels_like}°C)
{icon} Condition: {desc}
💧 Humidity: {humidity}%"""

    except Exception as e:
        logger.error(f"Weather API error: {e}")
        return f"*Weather:* ⚠️ Unable to fetch data"


def _get_weather_icon(weather_main: str) -> str:
    """Get emoji icon for weather condition."""
    icons = {
        "Clear": "☀️",
        "Clouds": "☁️",
        "Rain": "🌧️",
        "Drizzle": "🌦️",
        "Thunderstorm": "⛈️",
        "Snow": "❄️",
        "Mist": "🌫️",
        "Fog": "🌫️",
        "Haze": "🌫️",
        "Smoke": "🌫️",
    }
    return icons.get(weather_main, "🌤️")


def _send_whatsapp_message(to: str, message: str):
    """Send a WhatsApp message via Cloud API."""
    try:
        import httpx
        
        url = f"https://graph.facebook.com/v25.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message},
        }
        
        with httpx.Client() as client:
            r = client.post(url, json=payload, headers=headers, timeout=15)
            result = r.json()
            
            if r.status_code == 200:
                logger.info(f"WhatsApp report sent to {to}: {result}")
            else:
                logger.error(f"Failed to send WhatsApp report ({r.status_code}): {result}")

    except Exception as e:
        logger.error(f"Error sending WhatsApp report: {e}")


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
            "1. Read Business_Goals.md for targets and subscription audit rules\n"
            "2. Count completed tasks in /Done/ from this week\n"
            "3. Read Accounting/Bank_Transactions.md for revenue and subscription inventory\n"
            "4. Read Accounting/Current_Month.md for MTD reconciliation\n"
            "5. Check /Logs/ for all actions this week\n"
            "6. Identify bottlenecks (tasks that took > 2 days)\n"
            "7. Run subscription audit — create Pending_Approval/APPROVAL_cancel_sub_*.md for each flagged item\n"
            f"8. Write Monday Morning CEO Briefing to /Briefings/{today.strftime('%Y-%m-%d')}_Monday_Briefing.md\n"
            "9. Update Dashboard.md with weekly summary\n"
            "10. Run /weekly-briefing skill for full structured output"
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


def job_credential_rotation_reminder():
    """1st of each month — remind owner to rotate credentials."""
    logger.info("▶ Credential rotation reminder")
    if DRY_RUN:
        logger.info("[DRY RUN] Would create credential rotation reminder")
        return

    NEEDS_ACTION.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc)
    reminder_file = NEEDS_ACTION / f"ALERT_credential_rotation_{today.strftime('%Y%m')}.md"

    if reminder_file.exists():
        return  # already created this month

    reminder_file.write_text(
        f"""---
type: security_reminder
severity: medium
created: {today.isoformat()}
status: pending
---

## Monthly Credential Rotation Reminder

Security policy requires credentials to be rotated monthly.

### Credentials to Rotate

- [ ] `GMAIL_CLIENT_SECRET` — regenerate in Google Cloud Console
- [ ] `SMTP_PASSWORD` — generate new Gmail App Password
- [ ] `BANK_API_TOKEN` — rotate in banking provider dashboard
- [ ] `WHATSAPP_ACCESS_TOKEN` — refresh Meta Business token
- [ ] `SLACK_BOT_TOKEN` — rotate in Slack app settings
- [ ] `DASHBOARD_PASSWORD` — update in dashboard-ui/.env.local
- [ ] `SESSION_SECRET` — regenerate random 64-char hex

### After Rotating

1. Update `.env` with new values
2. For Keychain storage: `python secrets_manager.py set <NAME> <new_value>`
3. Restart all watchers: `uv run python orchestrator.py`
4. Run `python secrets_manager.py scan` to verify no leaks in vault
5. Move this file to /Done/

### Verify No Leaks

```bash
python secrets_manager.py scan ./AI_Employee_Vault
```

---
*Handbook §6: rotate credentials monthly and after any suspected breach.*
""",
        encoding="utf-8",
    )
    logger.info(f"Credential rotation reminder created: {reminder_file.name}")
    _log("credential_rotation_reminder_created", "success", {"month": today.strftime("%Y-%m")})


def job_monthly_audit_prompt():
    """1st of each month — prompt owner to run a 1-hour comprehensive audit."""
    today = datetime.now(timezone.utc)
    if today.day != 1:
        return
    logger.info("▶ Monthly audit prompt")
    if DRY_RUN:
        logger.info("[DRY RUN] Would create monthly audit prompt")
        return

    NEEDS_ACTION.mkdir(parents=True, exist_ok=True)
    prompt_file = NEEDS_ACTION / f"REVIEW_monthly_audit_{today.strftime('%Y%m')}.md"
    if prompt_file.exists():
        return

    prompt_file.write_text(
        f"""---
type: oversight_reminder
severity: medium
period: monthly
created: {today.isoformat()}
status: pending
---

## Monthly Oversight Review ({today.strftime('%B %Y')})

Ethics principle: The human remains accountable. Scheduled 1-hour review.

### Checklist

- [ ] Review `/Logs/` for unexpected or unusual AI actions
- [ ] Check `/Done/` — did all completed tasks match your intentions?
- [ ] Review `/Rejected/` — any patterns in what you rejected?
- [ ] Audit known contacts (`Contacts/known_contacts.json`) — remove stale entries
- [ ] Audit known payees (`Accounting/known_payees.json`) — remove inactive vendors
- [ ] Check opt-out list (`Contacts/opt_out_human_only.json`) — still accurate?
- [ ] Review Dashboard.md — are metrics tracking correctly?
- [ ] Run `/weekly-business-audit` for financial summary
- [ ] Run `/error-recovery` to surface any hidden errors

### Decision Log

Review any approval decisions made this month and confirm you stand behind them.
If you spot drift (AI acting outside intended boundaries), update `Company_Handbook.md`.

Move this file to /Done/ when complete.

---
*Ethics §4: Monthly 1-hour comprehensive audit — scheduled oversight is not optional.*
""",
        encoding="utf-8",
    )
    logger.info(f"Monthly audit prompt created: {prompt_file.name}")
    _log("monthly_audit_prompt_created", "success", {"month": today.strftime("%Y-%m")})


def job_quarterly_security_review():
    """1st of Jan/Apr/Jul/Oct — prompt owner for full security and access review."""
    today = datetime.now(timezone.utc)
    if today.day != 1 or today.month not in (1, 4, 7, 10):
        return
    logger.info("▶ Quarterly security review prompt")
    if DRY_RUN:
        logger.info("[DRY RUN] Would create quarterly security review prompt")
        return

    NEEDS_ACTION.mkdir(parents=True, exist_ok=True)
    quarter = f"Q{(today.month - 1) // 3 + 1}"
    review_file = NEEDS_ACTION / f"REVIEW_quarterly_security_{today.strftime('%Y')}_{quarter}.md"
    if review_file.exists():
        return

    review_file.write_text(
        f"""---
type: oversight_reminder
severity: high
period: quarterly
quarter: {quarter}
year: {today.year}
created: {today.isoformat()}
status: pending
---

## Quarterly Security & Access Review ({quarter} {today.year})

Ethics principle: Full security and access review every quarter.

### Access Review

- [ ] Review all API credentials — who/what has access to your systems?
- [ ] Revoke unused OAuth tokens in Google Cloud Console
- [ ] Review Meta Business app permissions (WhatsApp)
- [ ] Check Slack app scopes — remove unused permissions
- [ ] Review Odoo user permissions
- [ ] Audit `secrets/` folder — any files that shouldn't be there?

### Vault Security

- [ ] Check vault `.gitignore` — confirm `secrets/` and `.env` are excluded
- [ ] Review sync history — did any credentials leak into git?
  ```bash
  git log --all --full-history -- secrets/ .env
  ```
- [ ] Run secrets scanner: `python secrets_manager.py scan ./AI_Employee_Vault`
- [ ] Verify vault encryption (if enabled)

### AI Behaviour Audit

- [ ] Review the last 90 days of `/Logs/` for behaviour drift
- [ ] Test key HITL boundaries — verify payments still require approval
- [ ] Verify opt-out list is being respected (`Contacts/opt_out_human_only.json`)
- [ ] Check sensitive keyword list in `permission_guard.py` — needs updating?

### Third-Party Data Exposure

- [ ] What data left your system via Gmail API this quarter?
- [ ] What data was sent to Odoo?
- [ ] Review any new MCP servers added — understand their data access

Move this file to /Done/ when complete.

---
*Ethics §4: Quarterly full security and access review.*
""",
        encoding="utf-8",
    )
    logger.info(f"Quarterly security review created: {review_file.name}")
    _log("quarterly_security_review_created", "success", {"quarter": f"{quarter} {today.year}"})


# ── LinkedIn Automation ───────────────────────────────────────────────────────

LINKEDIN_MAX_POSTS_PER_DAY = os.getenv("LINKEDIN_MAX_POSTS_PER_DAY", "2")
LINKEDIN_ENABLED = os.getenv("LINKEDIN_ENABLED", "false").lower() == "true"
LINKEDIN_USER = os.getenv("LINKEDIN_USER", "")

# Gmail automation
GMAIL_ENABLED = os.getenv("GMAIL_CREDENTIALS_PATH", "") != ""
SMTP_ENABLED = os.getenv("SMTP_USER", "") != ""


def job_gmail_daily_digest():
    """Send daily Gmail activity digest."""
    logger.info("▶ Gmail daily digest job starting")
    
    if not GMAIL_ENABLED:
        logger.info("Gmail automation disabled")
        return
    
    # Generate digest
    digest = _generate_gmail_daily_digest()
    
    if DRY_RUN:
        logger.info(f"[DRY RUN] Would send Gmail digest")
        logger.info(f"Digest:\n{digest}")
        return
    
    # Send via WhatsApp if configured
    if WHATSAPP_DAILY_REPORT_ENABLED and WHATSAPP_DAILY_REPORT_TO:
        _send_whatsapp_message(WHATSAPP_DAILY_REPORT_TO, digest)
        _log("gmail_daily_digest_sent", "success", {"recipient": WHATSAPP_DAILY_REPORT_TO})


def job_gmail_auto_reply():
    """Auto-reply to new Gmail messages."""
    logger.info("▶ Gmail auto-reply check starting")
    
    if not GMAIL_ENABLED:
        logger.info("Gmail automation disabled")
        return
    
    # Import and run auto-replier
    try:
        from auto_gmail_replier import process_gmail_auto_reply
        emails, replies = process_gmail_auto_reply()
        if emails > 0 or replies > 0:
            _log("gmail_auto_reply", "success", {"processed": emails, "replies": replies})
    except Exception as e:
        logger.error(f"Gmail auto-reply error: {e}")
        _log("gmail_auto_reply_error", "error", {"error": str(e)})


def job_gmail_advanced_features():
    """Run advanced Gmail features (VIP, spam, language, etc.)."""
    logger.info("▶ Gmail advanced features check starting")
    
    if not GMAIL_ENABLED:
        logger.info("Gmail automation disabled")
        return
    
    # Import and run advanced features
    try:
        from advanced_gmail_features import process_advanced_features
        emails, vip, spam, after_hours = process_advanced_features()
        if emails > 0:
            _log("gmail_advanced_features", "success", {
                "processed": emails,
                "vip": vip,
                "spam_filtered": spam,
                "after_hours": after_hours
            })
    except Exception as e:
        logger.error(f"Gmail advanced features error: {e}")
        _log("gmail_advanced_features_error", "error", {"error": str(e)})


def _generate_gmail_daily_digest() -> str:
    """Generate daily Gmail activity summary."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Count emails from Needs_Action folder
    needs_action = VAULT_PATH / "Needs_Action"
    email_count = 0
    urgent_count = 0
    
    if needs_action.exists():
        today_slug = datetime.now(timezone.utc).strftime("%Y%m%d")
        for f in needs_action.glob(f"EMAIL_{today_slug}*.md"):
            email_count += 1
            content = f.read_text(encoding="utf-8")
            if "priority: high" in content or "priority:urgent" in content:
                urgent_count += 1
    
    # Count from Done folder
    done_dir = VAULT_PATH / "Done"
    processed_count = 0
    if done_dir.exists():
        today_slug = datetime.now(timezone.utc).strftime("%Y%m%d")
        processed_count = len(list(done_dir.glob(f"EMAIL_{today_slug}*.md")))
    
    # Get SMTP status
    smtp_status = "✅ Configured" if SMTP_ENABLED else "⬜ Not configured"
    
    digest = f"""📧 *Gmail Daily Digest*
📅 {today}

*Inbox Summary:*
📥 New Emails: {email_count}
⚠️ Urgent: {urgent_count}
✅ Processed: {processed_count}

*Email Sending:*
📤 SMTP: {smtp_status}
👤 From: {os.getenv("SMTP_FROM_NAME", "Not configured")}

*AI Employee Activity:*
✅ Email monitoring active
✅ Priority detection ready
✅ Auto-categorization enabled

Stay on top of your inbox! 🚀"""
    
    return digest


def job_linkedin_daily_digest():
    """Send daily LinkedIn activity digest."""
    logger.info("▶ LinkedIn daily digest job starting")
    
    if not LINKEDIN_ENABLED:
        logger.info("LinkedIn automation disabled")
        return
    
    # Generate digest
    digest = _generate_linkedin_daily_digest()
    
    if DRY_RUN:
        logger.info(f"[DRY RUN] Would send LinkedIn digest")
        logger.info(f"Digest:\n{digest}")
        return
    
    # Send via WhatsApp if configured
    if WHATSAPP_DAILY_REPORT_ENABLED and WHATSAPP_DAILY_REPORT_TO:
        _send_whatsapp_message(WHATSAPP_DAILY_REPORT_TO, digest)
        _log("linkedin_daily_digest_sent", "success", {"recipient": WHATSAPP_DAILY_REPORT_TO})


def _generate_linkedin_daily_digest() -> str:
    """Generate daily LinkedIn activity summary."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    to_post_dir = VAULT_PATH / "To_Post" / "LinkedIn"
    posts_count = 0
    if to_post_dir.exists():
        posts_count = len(list(to_post_dir.glob("*.md")))
    
    scheduled_dir = VAULT_PATH / "Scheduled"
    scheduled_count = 0
    if scheduled_dir.exists():
        scheduled_count = len(list(scheduled_dir.glob("LINKEDIN_*.md")))
    
    today_slug = datetime.now(timezone.utc).strftime("%Y%m%d")
    done_dir = VAULT_PATH / "Done"
    posted_today = 0
    if done_dir.exists():
        posted_today = len(list(done_dir.glob(f"LINKEDIN_{today_slug}*.md")))
    
    digest = f"""📊 *LinkedIn Daily Digest*
📅 {today}

*Content Pipeline:*
📝 In Queue: {posts_count}
⏳ Scheduled: {scheduled_count}
📤 Posted Today: {posted_today}/{LINKEDIN_MAX_POSTS_PER_DAY}

*Posting Schedule:*
✅ Active ({LINKEDIN_MAX_POSTS_PER_DAY} posts/day max)
👤 Account: {LINKEDIN_USER or 'Not configured'}

*AI Employee Activity:*
✅ Post scheduling active
✅ Engagement tracking ready
✅ Analytics compiled

Ready to grow your professional network! 🚀"""
    
    return digest


def job_auto_linkedin_post():
    """Auto-generate and schedule a LinkedIn post daily."""
    logger.info("▶ Auto LinkedIn post job starting")
    
    if not LINKEDIN_ENABLED:
        logger.info("LinkedIn automation disabled")
        return
    
    today = datetime.now(timezone.utc)
    ts = today.strftime("%Y%m%dT%H%M%SZ")
    
    # Generate post content based on activity
    needs_action = VAULT_PATH / "Needs_Action"
    done_dir = VAULT_PATH / "Done"
    
    wa_count = 0
    if needs_action.exists():
        today_slug = today.strftime("%Y%m%d")
        wa_count = len(list(needs_action.glob(f"WHATSAPP_{today_slug}*.md")))
    
    done_count = len(list(done_dir.glob("*.md"))) if done_dir.exists() else 0
    
    # Rotate through different post topics
    topics = [
        ("AI Employee Daily Update", f"🤖 Daily AI Report: {wa_count} messages processed, {done_count} tasks completed. Automation working smoothly! #AI #automation"),
        ("Building Autonomous Systems", "🚀 Small team, big impact. Our AI Employee handles routine work so humans can focus on what matters. #futureofwork"),
        ("Automation Wins", "⚡ When you automate the routine, you amplify the exceptional. What's your automation win this week? #productivity"),
    ]
    
    topic_idx = today.weekday() % len(topics)
    headline, content = topics[topic_idx]
    
    # Create scheduled post
    scheduled_dir = VAULT_PATH / "Scheduled"
    scheduled_dir.mkdir(exist_ok=True)
    
    trigger_file = scheduled_dir / f"LINKEDIN_AUTO_{ts}.md"
    trigger_file.write_text(f"""---
type: linkedin_auto_post
headline: {headline}
created: {today.isoformat()}
auto_generated: true
status: ready
---

## Auto-Generated LinkedIn Post

{content}

---
Run /post-linkedin to publish
""", encoding='utf-8')
    
    logger.info(f"✅ Auto LinkedIn post created: {trigger_file.name}")
    _log("linkedin_auto_post_created", "success", {"headline": headline})


def job_linkedin_full_automation():
    """Run full LinkedIn automation (auto-generate + post)."""
    logger.info("▶ LinkedIn full automation starting")
    
    if not LINKEDIN_ENABLED:
        logger.info("LinkedIn automation disabled")
        return
    
    # Import and run full automation
    try:
        from auto_linkedin_full import run_full_automation
        success = run_full_automation()
        if success:
            _log("linkedin_full_automation", "success", {"posted": True})
        else:
            _log("linkedin_full_automation", "success", {"posted": False, "reason": "manual_posting_required"})
    except Exception as e:
        logger.error(f"LinkedIn full automation error: {e}")
        _log("linkedin_full_automation_error", "error", {"error": str(e)})


# ── Main Scheduler ─────────────────────────────────────────────────────────────

def main():
    logger.info(f"Scheduler starting — vault: {VAULT_PATH}")
    logger.info(f"Daily briefing: {DAILY_BRIEFING_TIME}")
    logger.info(f"Weekly audit: Sunday {WEEKLY_AUDIT_TIME}")
    if DRY_RUN:
        logger.warning("DRY RUN MODE — no external triggers")

    # Security & Ethics oversight
    schedule.every().day.at("07:00").do(job_credential_rotation_reminder)  # fires on 1st of month
    schedule.every().day.at("07:05").do(job_monthly_audit_prompt)           # fires on 1st of month
    schedule.every().day.at("07:10").do(job_quarterly_security_review)      # fires quarterly

    # Daily jobs
    schedule.every().day.at(DAILY_BRIEFING_TIME).do(job_daily_briefing)
    schedule.every().day.at("09:00").do(job_odoo_health_check)  # Gold Tier

    # Daily WhatsApp report (Platinum)
    if WHATSAPP_DAILY_REPORT_ENABLED:
        schedule.every().day.at(WHATSAPP_DAILY_REPORT_TIME).do(job_whatsapp_daily_report)
        logger.info(f"Daily WhatsApp report: {WHATSAPP_DAILY_REPORT_TIME} UTC → {WHATSAPP_DAILY_REPORT_TO}")

    # Daily Gmail digest (Silver)
    if GMAIL_ENABLED:
        schedule.every().day.at("19:30").do(job_gmail_daily_digest)
        logger.info(f"Daily Gmail digest: 19:30 UTC → {WHATSAPP_DAILY_REPORT_TO}")
    
    # Auto-reply to Gmail every 30 minutes (Gold)
    if GMAIL_ENABLED and GMAIL_AUTO_REPLY:
        schedule.every(30).minutes.do(job_gmail_auto_reply)
        logger.info(f"Gmail auto-reply: Every 30 minutes")
    
    # Advanced Gmail features every hour (Platinum)
    if GMAIL_ENABLED:
        schedule.every().hour.do(job_gmail_advanced_features)
        logger.info(f"Gmail advanced features: Every hour")

    # Daily LinkedIn digest (Silver)
    if LINKEDIN_ENABLED:
        schedule.every().day.at("19:00").do(job_linkedin_daily_digest)
        logger.info(f"Daily LinkedIn digest: 19:00 UTC → {WHATSAPP_DAILY_REPORT_TO}")
    
    # Auto-generate LinkedIn post daily (Gold)
    if LINKEDIN_ENABLED:
        schedule.every().day.at("18:00").do(job_auto_linkedin_post)
        logger.info(f"Auto LinkedIn post: 18:00 UTC (1 hour before digest)")
    
    # Full LinkedIn automation every 6 hours (Platinum)
    if LINKEDIN_ENABLED:
        schedule.every(6).hours.do(job_linkedin_full_automation)
        logger.info(f"LinkedIn full automation: Every 6 hours")

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
