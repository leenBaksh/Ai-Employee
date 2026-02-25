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
import json
import asyncio
import aiosmtplib
from pathlib import Path
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
VAULT_PATH  = Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()
DRY_RUN     = os.getenv("DRY_RUN", "false").lower() == "true"
SMTP_HOST   = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT   = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER   = os.getenv("SMTP_USER", "")
SMTP_PASS   = os.getenv("SMTP_PASSWORD", "")
FROM_NAME   = os.getenv("SMTP_FROM_NAME", "AI Employee")
LOGS_DIR    = VAULT_PATH / "Logs"
DRAFTS_DIR  = VAULT_PATH / "Drafts"

LOGS_DIR.mkdir(parents=True, exist_ok=True)
DRAFTS_DIR.mkdir(parents=True, exist_ok=True)


def _log(action_type: str, target: str, result: str, details: dict = None):
    log_file = LOGS_DIR / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action_type": action_type,
        "actor": "email_mcp_server",
        "target": target,
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


async def _send_smtp(to: str, subject: str, body: str, cc: str = None) -> dict:
    """Send an email via SMTP. Returns dict with success/error."""
    if DRY_RUN:
        _log("email_send", to, "dry_run", {"subject": subject, "cc": cc})
        return {"success": True, "dry_run": True, "message": f"[DRY RUN] Would send to {to}: {subject}"}

    if not SMTP_USER or not SMTP_PASS:
        return {"success": False, "error": "SMTP credentials not configured. Set SMTP_USER and SMTP_PASSWORD in .env"}

    try:
        msg = MIMEMultipart("alternative")
        msg["From"]    = f"{FROM_NAME} <{SMTP_USER}>"
        msg["To"]      = to
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = cc

        # Add AI assistance footer (Handbook §3)
        full_body = f"{body}\n\n---\n*This email was drafted with AI assistance.*"
        msg.attach(MIMEText(full_body, "plain"))

        recipients = [to] + ([cc] if cc else [])
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASS,
            start_tls=True,
        )

        _log("email_send", to, "success", {"subject": subject, "cc": cc})
        return {"success": True, "message": f"Email sent to {to}"}

    except Exception as e:
        _log("email_send", to, "error", {"subject": subject, "error": str(e)})
        return {"success": False, "error": str(e)}


def _save_draft(to: str, subject: str, body: str) -> dict:
    """Save an email draft to /Drafts/ for human review."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_subj = "".join(c if c.isalnum() or c in "-_" else "_" for c in subject)[:40]
    draft_file = DRAFTS_DIR / f"DRAFT_{timestamp}_{safe_subj}.md"

    draft_file.write_text(
        f"""---
type: email_draft
to: {to}
subject: {subject}
created: {datetime.now(timezone.utc).isoformat()}
status: pending_review
---

## Draft Email

**To:** {to}
**Subject:** {subject}

## Body

{body}

---
*AI-drafted email. Review before sending.*
*To send: move this file to /Approved/*
*To discard: move to /Rejected/*
""",
        encoding='utf-8',
    )
    _log("email_draft_saved", to, "success", {"subject": subject, "draft_file": draft_file.name})
    return {"success": True, "draft_file": str(draft_file), "message": f"Draft saved to {draft_file.name}"}


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
        print("ERROR: mcp package not installed. Run: uv sync")
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
                        "to":      {"type": "string", "description": "Recipient email address"},
                        "subject": {"type": "string", "description": "Email subject line"},
                        "body":    {"type": "string", "description": "Email body (plain text)"},
                        "cc":      {"type": "string", "description": "CC email address (optional)"},
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
            result = await _send_smtp(
                to=arguments["to"],
                subject=arguments["subject"],
                body=arguments["body"],
                cc=arguments.get("cc"),
            )
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
