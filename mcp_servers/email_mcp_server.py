"""
email_mcp_server.py — Email MCP Server for the AI Employee.

Exposes three MCP tools to Claude:
  - send_email(to, subject, body, cc?)   → sends via SMTP (requires /Approved/ file)
  - draft_email(to, subject, body)       → saves draft to /Drafts/ for review
  - list_drafts()                        → lists pending email drafts

Security (Handbook §3 & §6):
  - NEVER sends to unknown recipients without explicit approval
  - All sends are logged to /Logs/
  - Respects DRY_RUN mode

Setup:
  Set in .env:
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_NAME

Run as MCP server (stdio transport):
    uv run email-mcp

Configure in Claude Code (~/.claude.json or project .claude/mcp.json):
    {
      "mcpServers": {
        "email": {
          "command": "uv",
          "args": ["run", "--directory", "/path/to/ai-employee", "email-mcp"],
          "env": { "VAULT_PATH": "./AI_Employee_Vault" }
        }
      }
    }
"""

import os
import sys
import json
import base64
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from rate_limiter import get_limiter, RateLimitExceededError
from audit_logger import write_log_entry, infer_approval
from permission_guard import check as permission_check, add_known_contact
from retry_handler import with_retry_async, classify_error

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
VAULT_PATH   = Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()
DRY_RUN      = os.getenv("DRY_RUN", "true").lower() == "true"
SMTP_USER    = os.getenv("SMTP_USER", "")
FROM_NAME    = os.getenv("SMTP_FROM_NAME", "AI Employee")
GMAIL_CREDS  = os.getenv("GMAIL_CREDENTIALS_PATH", "./secrets/gmail_credentials.json")
GMAIL_TOKEN  = os.getenv("GMAIL_TOKEN_PATH", "./secrets/gmail_token.json")
LOGS_DIR     = VAULT_PATH / "Logs"
DRAFTS_DIR   = VAULT_PATH / "Drafts"
QUEUE_DIR    = VAULT_PATH / "Queue"   # §7.3 — offline queue when Gmail API is down

LOGS_DIR.mkdir(parents=True, exist_ok=True)
DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
QUEUE_DIR.mkdir(parents=True, exist_ok=True)


def _log(action_type: str, target: str, result: str, details: dict = None):
    approval_status, approved_by = infer_approval(action_type, DRY_RUN)
    write_log_entry(
        logs_dir=LOGS_DIR,
        action_type=action_type,
        actor="email_mcp_server",
        target=target,
        result=result,
        parameters=details or {},
        approval_status=approval_status,
        approved_by=approved_by,
    )


@with_retry_async(max_attempts=3, base_delay=2, max_delay=30)
async def _send_gmail_api(to: str, subject: str, body: str, cc: str = None,
                          attachment: str = None) -> dict:
    """Send an email via Gmail API (OAuth2) — retries on transient network errors.
    attachment: optional path to a file (e.g. PDF invoice) to attach.
    """
    if DRY_RUN:
        _log("email_send", to, "dry_run", {"subject": subject, "cc": cc})
        return {"success": True, "dry_run": True, "message": f"[DRY RUN] Would send to {to}: {subject}"}

    # Rate limiting — max 10 emails per hour
    try:
        get_limiter(VAULT_PATH).check("email_send")
    except RateLimitExceededError as e:
        _log("email_send", to, "rate_limited", {"error": str(e)})
        return {"success": False, "error": str(e), "rate_limited": True}

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        token_data = json.loads(Path(GMAIL_TOKEN).read_text(encoding="utf-8"))
        creds = Credentials.from_authorized_user_info(token_data)
        service = build("gmail", "v1", credentials=creds)

        msg = MIMEMultipart("alternative")
        msg["From"]    = f"{FROM_NAME} <{SMTP_USER}>"
        msg["To"]      = to
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = cc

        full_body = f"{body}\n\n---\n*This email was drafted with AI assistance.*"
        msg.attach(MIMEText(full_body, "plain"))

        if attachment:
            attach_path = Path(attachment)
            if attach_path.exists():
                with open(attach_path, "rb") as f:
                    part = MIMEApplication(f.read(), _subtype="pdf")
                    part.add_header("Content-Disposition", "attachment", filename=attach_path.name)
                    msg.attach(part)

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()

        # §6.4 — register as known contact after successful send
        add_known_contact(to, VAULT_PATH)
        _log("email_send", to, "success", {"subject": subject, "cc": cc})
        return {"success": True, "message": f"Email sent to {to}"}

    except Exception as e:
        # Classify before logging — lets the @with_retry_async decorator retry if transient
        raise classify_error(e) from e


def _save_draft(to: str, subject: str, body: str, cc: str = "") -> dict:
    """Save an email draft to /Drafts/ for human review."""
    # §6.4 Permission check — annotates the draft file accordingly
    perm = permission_check("email", VAULT_PATH, to=to, cc=cc)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_subj = "".join(c if c.isalnum() or c in "-_" else "_" for c in subject)[:40]
    draft_file = DRAFTS_DIR / f"DRAFT_{timestamp}_{safe_subj}.md"

    approval_note = (
        "*Known contact — may be approved without additional review.*"
        if not perm.requires_approval
        else "*New contact or bulk send — explicit human approval required before sending.*"
    )

    draft_file.write_text(
        f"""---
type: email_draft
to: {to}
subject: {subject}
created: {datetime.now(timezone.utc).isoformat()}
status: pending_review
permission_mode: {perm.mode}
permission_reason: {perm.reason}
---

## Draft Email

**To:** {to}
**Subject:** {subject}

## Body

{body}

---
*AI-drafted email. Review before sending.*
{approval_note}
*To send: move this file to /Approved/*
*To discard: move to /Rejected/*
""",
        encoding='utf-8',
    )
    _log("email_draft_saved", to, "success", {
        "subject": subject, "draft_file": draft_file.name,
        "permission_mode": perm.mode, "permission_reason": perm.reason,
    })
    return {
        "success": True,
        "draft_file": str(draft_file),
        "permission_mode": perm.mode,
        "permission_reason": perm.reason,
        "message": f"Draft saved to {draft_file.name}. {str(perm)}",
    }


def _queue_email(to: str, subject: str, body: str, cc: str, error: str) -> dict:
    """
    §7.3 Graceful Degradation — Gmail API down.
    Queue the email locally so it can be sent when the API is restored.
    Writes to /Queue/EMAIL_QUEUED_*.md — orchestrator retry loop picks these up.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    queue_file = QUEUE_DIR / f"EMAIL_QUEUED_{ts}.md"
    queue_file.write_text(
        f"""---
type: queued_email
to: {to}
subject: {subject}
cc: {cc or ""}
queued_at: {datetime.now(timezone.utc).isoformat()}
queued_reason: {error}
status: queued
retry_count: 0
---

## Queued Email (Gmail API Unavailable)

**To:** {to}
**Subject:** {subject}

{body}

---
*Queued by §7.3 graceful degradation — will be sent when Gmail API is restored.*
*Orchestrator retry loop processes /Queue/EMAIL_QUEUED_*.md files.*
""",
        encoding="utf-8",
    )
    _log("email_queued", to, "queued", {
        "subject": subject, "queue_file": queue_file.name, "queued_reason": error,
    })
    return {
        "success": False,
        "queued": True,
        "queue_file": queue_file.name,
        "message": f"Gmail API unavailable — email queued at {queue_file.name}. Will send when API is restored.",
    }


def _list_drafts() -> dict:
    """List all pending email drafts."""
    drafts = []
    for f in sorted(DRAFTS_DIR.glob("DRAFT_*.md")):
        try:
            content = f.read_text()
            lines = content.split("\n")
            to = next((l.replace("to: ", "") for l in lines if l.startswith("to: ")), "?")
            subj = next((l.replace("subject: ", "") for l in lines if l.startswith("subject: ")), "?")
            drafts.append({"file": f.name, "to": to, "subject": subj})
        except Exception:
            drafts.append({"file": f.name})
    return {"drafts": drafts, "count": len(drafts)}


# ── MCP Server ────────────────────────────────────────────────────────────────
def main():
    """Run the Email MCP Server using stdio transport."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp import types
    except ImportError:
        sys.stderr.write("ERROR: mcp package not installed. Run: uv sync\n")
        raise SystemExit(1)

    server = Server("email-mcp")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="send_email",
                description=(
                    "Send an email via SMTP. Only use when an approved file exists in /Approved/. "
                    "Always adds AI assistance footer per Company Handbook §3."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to":         {"type": "string", "description": "Recipient email address"},
                        "subject":    {"type": "string", "description": "Email subject line"},
                        "body":       {"type": "string", "description": "Email body (plain text)"},
                        "cc":         {"type": "string", "description": "CC email address (optional)"},
                        "attachment": {"type": "string", "description": "Absolute path to file to attach, e.g. /Vault/Invoices/INVOICE_*.pdf (optional)"},
                    },
                    "required": ["to", "subject", "body"],
                },
            ),
            types.Tool(
                name="draft_email",
                description=(
                    "Save an email as a draft in /Drafts/ for human review before sending. "
                    "Use this when generating a reply that needs human approval."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to":      {"type": "string"},
                        "subject": {"type": "string"},
                        "body":    {"type": "string"},
                    },
                    "required": ["to", "subject", "body"],
                },
            ),
            types.Tool(
                name="list_drafts",
                description="List all pending email drafts in /Drafts/ awaiting review.",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        if name == "send_email":
            try:
                result = await _send_gmail_api(
                    to=arguments["to"],
                    subject=arguments["subject"],
                    body=arguments["body"],
                    cc=arguments.get("cc"),
                    attachment=arguments.get("attachment"),
                )
            except Exception as e:
                from retry_handler import TransientError, SystemError as AISystemError
                _log("email_send", arguments.get("to", "?"), "error",
                     {"error": str(e), "error_category": getattr(e, "category", "unknown")})
                # §7.3 — queue locally for transient/system failures; surface auth/logic immediately
                if isinstance(e, (TransientError, AISystemError)):
                    result = _queue_email(
                        to=arguments.get("to", ""),
                        subject=arguments.get("subject", ""),
                        body=arguments.get("body", ""),
                        cc=arguments.get("cc", ""),
                        error=str(e),
                    )
                else:
                    result = {"success": False, "error": str(e),
                              "error_category": getattr(e, "category", "unknown")}
        elif name == "draft_email":
            result = _save_draft(
                to=arguments["to"],
                subject=arguments["subject"],
                body=arguments["body"],
            )
        elif name == "list_drafts":
            result = _list_drafts()
        else:
            result = {"error": f"Unknown tool: {name}"}

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
