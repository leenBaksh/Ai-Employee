"""
dashboard_server.py — Live web dashboard for the AI Employee Vault.

Serves a real-time browser dashboard at http://localhost:8888/
with vault stats, agent health, task queue, and recent activity logs.

Endpoints:
  GET /                        → Renders templates/dashboard.html
  GET /api/stats               → Vault folder counts
  GET /api/health              → Agent health signals
  GET /api/tasks               → Needs_Action/ task list
  GET /api/approvals           → Pending_Approval/ list
  GET /api/done                → Done/ archive (newest-first, limit 100)
  GET /api/logs                → Log entries (?search=&result=&limit=)
  GET /api/stream              → SSE stream (full dashboard JSON every 5s)
  POST /api/approve/<filename> → Move Pending_Approval → Approved
  POST /api/reject/<filename>  → Move Pending_Approval → Rejected

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

import shutil
import urllib.request
import urllib.error
from flask import Flask, render_template, jsonify, Response, stream_with_context, request, abort
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

VAULT_PATH = Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8888"))
HEALTH_OFFLINE_THRESHOLD = int(os.getenv("HEALTH_OFFLINE_THRESHOLD", "300"))  # 5 minutes

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "http://172.16.0.1:3000"])


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
    for agent_id in ["local-01"]:
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


def get_service_connections() -> list:
    """
    Derive connection status for Gmail, WhatsApp, LinkedIn, and Odoo
    by inspecting the last N log entries for each service.
    Returns a list of connection dicts suitable for the dashboard.
    """
    # Scan today's + yesterday's log for recent entries
    logs_dir = VAULT_PATH / "Logs"
    entries: list[dict] = []
    for delta in (0, 1):
        day = (datetime.now(timezone.utc) - timedelta(days=delta)).strftime("%Y-%m-%d")
        log_file = logs_dir / f"{day}.json"
        if log_file.exists():
            try:
                entries.extend(json.loads(log_file.read_text(encoding="utf-8")))
            except Exception:
                pass

    # Keep only the most recent 500 entries to bound scan time
    entries = entries[-500:]

    # Service definitions: action_type prefixes to match + token/credential files to probe
    services = [
        {
            "id":      "gmail",
            "label":   "Gmail",
            "icon":    "✉️",
            "prefixes": ("gmail_poll", "email_send"),
            "token":    Path(os.getenv("GMAIL_TOKEN_PATH", "./secrets/gmail_token.json")),
        },
        {
            "id":      "whatsapp",
            "label":   "WhatsApp",
            "icon":    "💬",
            "prefixes": ("whatsapp_poll", "poll_error", "whatsapp_send"),
            "token":    None,  # Playwright-based — no token file
        },
        {
            "id":      "linkedin",
            "label":   "LinkedIn",
            "icon":    "💼",
            "prefixes": ("linkedin_post", "linkedin_trigger"),
            "token":    None,
        },
        {
            "id":      "odoo",
            "label":   "Odoo",
            "icon":    "🏢",
            "prefixes": ("odoo_get_", "odoo_create_"),
            "token":    None,
            "env_check": ("ODOO_URL", "ODOO_DB", "ODOO_USER", "ODOO_PASSWORD"),
        },
    ]

    results = []
    now_utc = datetime.now(timezone.utc)

    for svc in services:
        # Find last log entry for this service
        matches = [
            e for e in entries
            if any(str(e.get("action_type", "")).startswith(p) for p in svc["prefixes"])
        ]

        last_entry = matches[-1] if matches else None
        last_error = next(
            (e for e in reversed(matches) if e.get("result") == "error"), None
        )
        last_success = next(
            (e for e in reversed(matches) if e.get("result") in ("success", "dry_run")), None
        )

        # Determine status
        if svc.get("env_check"):
            missing = [v for v in svc["env_check"] if not os.getenv(v)]
            if missing:
                status = "not_configured"
                detail = f"Missing env vars: {', '.join(missing)}"
                results.append(_conn(svc, status, detail, last_success, last_error))
                continue

        if svc.get("token") and not svc["token"].exists():
            results.append(_conn(svc, "not_configured",
                                 "Token file not found — run setup", last_success, last_error))
            continue

        if last_error and (not last_success or
                           last_error.get("timestamp", "") > last_success.get("timestamp", "")):
            err_msg = str(last_error.get("parameters", {}).get("error", ""))[:80]
            if "name_not_resolved" in err_msg.lower() or "unable to find the server" in err_msg.lower():
                status, detail = "dns_error", "DNS resolution failed — check network"
            elif "not logged in" in err_msg.lower() or "qr" in err_msg.lower():
                status, detail = "auth_error", "Session expired — QR scan required"
            elif "403" in err_msg or "forbidden" in err_msg.lower():
                status, detail = "auth_error", "403 Forbidden — check API permissions"
            elif "401" in err_msg or "invalid_grant" in err_msg.lower():
                status, detail = "auth_error", "Token expired — re-run setup"
            else:
                status, detail = "error", err_msg or "Unknown error"
        elif last_success:
            ts = last_success.get("timestamp", "")
            try:
                age = (now_utc - datetime.fromisoformat(ts.replace("Z", "+00:00"))).total_seconds()
                detail = f"Last OK {int(age // 60)}m ago"
            except Exception:
                detail = "Connected"
            status = "connected"
        elif not last_entry:
            status, detail = "never_seen", "No activity in logs"
        else:
            status, detail = "unknown", "No recent successful poll"

        results.append(_conn(svc, status, detail, last_success, last_error))

    return results


def _conn(svc: dict, status: str, detail: str,
          last_success: dict | None, last_error: dict | None) -> dict:
    return {
        "id":           svc["id"],
        "label":        svc["label"],
        "icon":         svc["icon"],
        "status":       status,       # connected | error | auth_error | dns_error | not_configured | never_seen
        "detail":       detail,
        "last_success": (last_success or {}).get("timestamp"),
        "last_error":   (last_error or {}).get("timestamp"),
        "last_error_msg": str((last_error or {}).get("parameters", {}).get("error", ""))[:120],
    }


def get_task_list(folder: str = "Needs_Action", pattern: str = "*.md", limit: int = 20, newest_first: bool = False) -> list:
    """List files in a vault folder with age metadata."""
    d = VAULT_PATH / folder
    if not d.exists():
        return []
    now = time.time()
    files = []
    for f in sorted(d.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=newest_first):
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


def get_recent_logs(limit: int = 50, search: str = "", result_filter: str = "") -> list:
    """Load recent log entries from today's and yesterday's log files.

    Args:
        limit: Maximum entries to return (default 50).
        search: Case-insensitive keyword filter on action_type, target, result.
        result_filter: Exact-match filter on the result field.
    """
    logs_dir = VAULT_PATH / "Logs"
    if not logs_dir.exists():
        return []
    today = datetime.now(timezone.utc)
    dates_to_check = [
        today.strftime("%Y-%m-%d"),
        (today - timedelta(days=1)).strftime("%Y-%m-%d"),
        (today - timedelta(days=2)).strftime("%Y-%m-%d"),
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

    # Apply filters
    if search:
        kw = search.lower()
        entries = [
            e for e in entries
            if kw in (e.get("action_type") or "").lower()
            or kw in (e.get("target") or "").lower()
            or kw in str(e.get("result") or "").lower()
        ]
    if result_filter:
        entries = [e for e in entries if str(e.get("result") or "") == result_filter]

    return entries[:limit]


def _append_log(action_type: str, target: str, result: str, actor: str = "dashboard") -> None:
    """Append a single log entry to today's log file."""
    logs_dir = VAULT_PATH / "Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = logs_dir / f"{today}.json"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action_type": action_type,
        "actor": actor,
        "target": target,
        "result": result,
    }
    existing = []
    if log_file.exists():
        try:
            existing = json.loads(log_file.read_text(encoding="utf-8"))
            if not isinstance(existing, list):
                existing = []
        except Exception:
            existing = []
    existing.append(entry)
    log_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def get_full_dashboard() -> dict:
    """Combine all data into a single dashboard payload."""
    return {
        "stats":        get_vault_stats(),
        "health":       get_agent_health(),
        "connections":  get_service_connections(),
        "tasks":        get_task_list("Needs_Action"),
        "approvals":    get_task_list("Pending_Approval"),
        "logs":         get_recent_logs(20),
        "done_recent":  get_task_list("Done", pattern="*", limit=10, newest_first=True),
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


@app.route("/api/connections")
def api_connections():
    return jsonify(get_service_connections())


@app.route("/api/whatsapp/messages")
def api_whatsapp_messages():
    """Recent WhatsApp messages from vault task files."""
    msgs = []
    for folder in ("Done", "Needs_Action"):
        d = VAULT_PATH / folder
        if not d.exists():
            continue
        for f in sorted(d.glob("WHATSAPP_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]:
            try:
                content = f.read_text(encoding="utf-8")
                lines = content.splitlines()
                sender  = next((l.split(":",1)[1].strip() for l in lines if l.startswith("from:")), "Unknown")
                message = next((l.split(":",1)[1].strip() for l in lines if l.startswith("message:")), "")
                ts      = next((l.split(":",1)[1].strip() for l in lines if l.startswith("received:")), "")
                msgs.append({"file": f.name, "from": sender, "message": message,
                             "received": ts, "status": folder})
            except Exception:
                pass
    msgs.sort(key=lambda m: m.get("received",""), reverse=True)
    return jsonify({"messages": msgs[:20]})


@app.route("/api/whatsapp/draft", methods=["POST"])
def api_whatsapp_draft():
    """Queue a WhatsApp reply draft for approval."""
    body = request.json or {}
    to_number = body.get("to_number","").strip()
    message   = body.get("message","").strip()
    if not to_number or not message:
        return jsonify({"error": "to_number and message required"}), 400
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    pending = VAULT_PATH / "Pending_Approval"
    pending.mkdir(exist_ok=True)
    fname = f"APPROVAL_whatsapp_{ts}.md"
    (pending / fname).write_text(
        f"---\ntype: whatsapp_reply_approval\naction: send_whatsapp_message\n"
        f"to_number: {to_number}\nreply_text: {message}\ncreated: {datetime.now(timezone.utc).isoformat()}\nstatus: pending\n---\n\n"
        f"## WhatsApp Message — Approval Required\n\n**To:** {to_number}\n\n**Message:**\n{message}\n\n"
        f"Move to /Approved/ to send.\n", encoding="utf-8")
    _append_log("whatsapp_draft_created", to_number, "pending", actor="dashboard")
    return jsonify({"success": True, "approval_file": fname})


@app.route("/api/whatsapp/send", methods=["POST"])
def api_whatsapp_send():
    """Send a WhatsApp message directly via Meta Cloud API."""
    access_token    = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    if not access_token or not phone_number_id:
        return jsonify({"error": "WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID not configured"}), 503

    body      = request.json or {}
    to_number = body.get("to_number", "").strip().replace("+", "").replace(" ", "").replace("-", "")
    message   = body.get("message", "").strip()
    if not to_number or not message:
        return jsonify({"error": "to_number and message required"}), 400

    payload = json.dumps({
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message},
    }).encode("utf-8")

    url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        _append_log("whatsapp_sent", to_number, "success", actor="dashboard")
        # Save a record to Done/
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        done_dir = VAULT_PATH / "Done"
        done_dir.mkdir(exist_ok=True)
        (done_dir / f"WHATSAPP_{ts}_sent_to_{to_number[:15]}.md").write_text(
            f"---\ntype: whatsapp_sent\nto: {to_number}\nsent: {datetime.now(timezone.utc).isoformat()}\nstatus: sent\n---\n\n"
            f"## WhatsApp Sent\n\n**To:** {to_number}\n\n**Message:**\n{message}\n",
            encoding="utf-8",
        )
        return jsonify({"success": True, "meta_response": result})
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        _append_log("whatsapp_send_failed", to_number, "error", actor="dashboard")
        # Surface human-readable errors for common Meta error codes
        try:
            err_json = json.loads(err_body)
            code = err_json.get("error", {}).get("code")
            if code == 131030:
                return jsonify({"error": "Number not in allowed list — add it in Meta Developer → WhatsApp → API Setup → Manage phone number list"}), 502
            if code == 190:
                return jsonify({"error": "Access token expired — update WHATSAPP_ACCESS_TOKEN in .env"}), 502
            if code == 100:
                return jsonify({"error": "Phone Number ID not found — check WHATSAPP_PHONE_NUMBER_ID in .env"}), 502
        except Exception:
            pass
        return jsonify({"error": f"Meta API error {e.code}", "detail": err_body}), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/gmail/messages")
def api_gmail_messages():
    """Recent email task files from vault."""
    msgs = []
    for folder in ("Done", "Needs_Action"):
        d = VAULT_PATH / folder
        if not d.exists():
            continue
        for f in sorted(d.glob("EMAIL_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]:
            try:
                content = f.read_text(encoding="utf-8")
                lines   = content.splitlines()
                sender  = next((l.split(":",1)[1].strip() for l in lines if l.lower().startswith("from:")), "")
                subject = next((l.split(":",1)[1].strip() for l in lines if l.lower().startswith("subject:")), f.name)
                ts      = next((l.split(":",1)[1].strip() for l in lines if l.lower().startswith("received:")), "")
                msgs.append({"file": f.name, "from": sender, "subject": subject,
                             "received": ts, "status": folder})
            except Exception:
                pass
    msgs.sort(key=lambda m: m.get("received",""), reverse=True)
    return jsonify({"messages": msgs[:20]})


@app.route("/api/gmail/draft", methods=["POST"])
def api_gmail_draft():
    """Save an email draft to /Drafts/ for approval."""
    body    = request.json or {}
    to      = body.get("to","").strip()
    subject = body.get("subject","").strip()
    msg     = body.get("body","").strip()
    if not to or not subject or not msg:
        return jsonify({"error": "to, subject, body required"}), 400
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    drafts = VAULT_PATH / "Drafts"
    drafts.mkdir(exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in subject)[:40]
    fname = f"DRAFT_{ts}_{safe}.md"
    (drafts / fname).write_text(
        f"---\ntype: email_draft\nto: {to}\nsubject: {subject}\n"
        f"created: {datetime.now(timezone.utc).isoformat()}\nstatus: pending_review\n---\n\n"
        f"## Draft Email\n\n**To:** {to}\n**Subject:** {subject}\n\n## Body\n\n{msg}\n\n"
        f"---\n*Move to /Approved/ to send.*\n", encoding="utf-8")
    _append_log("email_draft_saved", to, "success", actor="dashboard")
    return jsonify({"success": True, "draft_file": fname})


@app.route("/api/odoo/summary")
def api_odoo_summary():
    """Read Odoo/accounting summary from vault files."""
    result: dict = {}
    month_file = VAULT_PATH / "Accounting" / "Current_Month.md"
    if month_file.exists():
        content = month_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            for key, field in [("**Income**","income"),("**Expenses**","expenses"),("**MTD Goal**","goal"),("**Net**","net")]:
                if key in line:
                    parts = line.split("|")
                    if len(parts) > 2:
                        try:
                            result[field] = float(parts[2].strip().replace("$","").replace(",",""))
                        except ValueError:
                            pass
    # Count invoices
    invoices_dir = VAULT_PATH / "Invoices"
    result["invoice_count"] = len(list(invoices_dir.glob("INVOICE_*.md"))) if invoices_dir.exists() else 0
    # Recent invoices
    recent = []
    if invoices_dir.exists():
        for f in sorted(invoices_dir.glob("INVOICE_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]:
            lines = f.read_text(encoding="utf-8").splitlines()
            customer = next((l.split(":",1)[1].strip() for l in lines if l.startswith("customer:")), f.stem)
            amount   = next((l.split(":",1)[1].strip() for l in lines if l.startswith("amount:")), "?")
            recent.append({"file": f.name, "customer": customer, "amount": amount})
    result["recent_invoices"] = recent
    return jsonify(result)


@app.route("/api/odoo/invoice", methods=["POST"])
def api_odoo_invoice():
    """Create an invoice approval request."""
    body     = request.json or {}
    customer = body.get("customer","").strip()
    amount   = body.get("amount","").strip()
    email    = body.get("email","").strip()
    desc     = body.get("description","Professional Services").strip()
    if not customer or not amount:
        return jsonify({"error": "customer and amount required"}), 400
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    pending = VAULT_PATH / "Pending_Approval"
    pending.mkdir(exist_ok=True)
    fname = f"APPROVAL_invoice_{ts}_{customer.replace(' ','_')[:20]}.md"
    (pending / fname).write_text(
        f"---\ntype: approval_request\naction: create_invoice\ncustomer: {customer}\n"
        f"amount: {amount}\nemail: {email}\ndescription: {desc}\n"
        f"created: {datetime.now(timezone.utc).isoformat()}\nstatus: pending\n---\n\n"
        f"## Invoice Approval — {customer}\n\n**Customer:** {customer}\n**Amount:** ${amount}\n"
        f"**Email:** {email or '(not provided)'}\n**Description:** {desc}\n\n"
        f"Move to /Approved/ to generate and send invoice.\n", encoding="utf-8")
    _append_log("invoice_approval_created", customer, "pending", actor="dashboard")
    return jsonify({"success": True, "approval_file": fname})


@app.route("/api/linkedin/posts")
def api_linkedin_posts():
    """List pending and recent LinkedIn posts."""
    posts = []
    for folder in ("To_Post/LinkedIn", "Done"):
        d = VAULT_PATH / folder
        if not d.exists():
            continue
        for f in sorted(d.glob("LINKEDIN_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:10]:
            try:
                content = f.read_text(encoding="utf-8")
                lines   = content.splitlines()
                status  = next((l.split(":",1)[1].strip() for l in lines if l.startswith("status:")), folder)
                body_lines = [l for l in content.split("---")[-1].splitlines() if l.strip() and not l.startswith("#")]
                preview = " ".join(body_lines)[:120]
                posts.append({"file": f.name, "status": status, "preview": preview,
                              "folder": folder.split("/")[-1]})
            except Exception:
                pass
    return jsonify({"posts": posts})


@app.route("/api/linkedin/draft", methods=["POST"])
def api_linkedin_draft():
    """Queue a LinkedIn post for approval."""
    body    = request.json or {}
    content = body.get("content","").strip()
    if not content:
        return jsonify({"error": "content required"}), 400
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    to_post = VAULT_PATH / "To_Post" / "LinkedIn"
    to_post.mkdir(parents=True, exist_ok=True)
    pending = VAULT_PATH / "Pending_Approval"
    pending.mkdir(exist_ok=True)
    post_fname = f"LINKEDIN_POST_{ts}.md"
    (to_post / post_fname).write_text(
        f"---\ntype: linkedin_post\nstatus: pending_approval\ncreated: {datetime.now(timezone.utc).isoformat()}\n---\n\n{content}\n",
        encoding="utf-8")
    approval_fname = f"APPROVAL_linkedin_{ts}.md"
    (pending / approval_fname).write_text(
        f"---\ntype: linkedin_post\naction: post_linkedin\npost_file: To_Post/LinkedIn/{post_fname}\n"
        f"created: {datetime.now(timezone.utc).isoformat()}\nstatus: pending\n---\n\n"
        f"## LinkedIn Post — Approval Required\n\n{content[:300]}\n\nMove to /Approved/ to publish.\n",
        encoding="utf-8")
    _append_log("linkedin_draft_created", "linkedin", "pending", actor="dashboard")
    return jsonify({"success": True, "post_file": post_fname, "approval_file": approval_fname})


@app.route("/api/tasks")
def api_tasks():
    return jsonify(get_task_list("Needs_Action"))


@app.route("/api/approvals")
def api_approvals():
    return jsonify(get_task_list("Pending_Approval"))


@app.route("/api/logs")
def api_logs():
    search = request.args.get("search", "").strip()
    result_filter = request.args.get("result", "").strip()
    limit = int(request.args.get("limit", "50"))
    return jsonify(get_recent_logs(limit=limit, search=search, result_filter=result_filter))


@app.route("/api/done")
def api_done():
    return jsonify(get_task_list("Done", pattern="*", limit=100, newest_first=True))


@app.route("/api/approve/<path:filename>", methods=["POST"])
def api_approve(filename):
    src = VAULT_PATH / "Pending_Approval" / filename
    dst = VAULT_PATH / "Approved" / filename
    if not src.exists():
        return jsonify({"error": "not found", "filename": filename}), 404
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    _append_log("approval_granted", filename, "approved", actor="dashboard")
    return jsonify({"status": "ok", "filename": filename})


@app.route("/api/reject/<path:filename>", methods=["POST"])
def api_reject(filename):
    src = VAULT_PATH / "Pending_Approval" / filename
    dst = VAULT_PATH / "Rejected" / filename
    if not src.exists():
        return jsonify({"error": "not found", "filename": filename}), 404
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    _append_log("approval_rejected", filename, "rejected", actor="dashboard")
    return jsonify({"status": "ok", "filename": filename})


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
