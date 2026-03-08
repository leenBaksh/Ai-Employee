"""
whatsapp_mcp_server.py — WhatsApp MCP Server for the AI Employee.

Exposes 3 MCP tools to Claude:
  - whatsapp_get_recent(limit?)   → read recent WhatsApp task files from vault
  - whatsapp_send_message(to, text) → HITL: creates Pending_Approval file (does NOT send)
  - whatsapp_get_status()         → check webhook server connectivity

Inbound messages are received by watchers/whatsapp_watcher.py (Meta Cloud API webhook).
Outbound messages require human approval — this MCP drafts them for the approval loop.

Run as MCP server (stdio transport):
    uv run whatsapp-mcp

Configure in .claude/mcp.json:
    {
      "whatsapp": {
        "command": "uv",
        "args": ["run", "--directory", ".", "whatsapp-mcp"],
        "env": { "VAULT_PATH": "./AI_Employee_Vault" }
      }
    }
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from rate_limiter import get_limiter, RateLimitExceededError

load_dotenv()

VAULT_PATH   = Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()
NEEDS_ACTION = VAULT_PATH / "Needs_Action"
PENDING      = VAULT_PATH / "Pending_Approval"
WEBHOOK_PORT = int(os.getenv("WHATSAPP_WEBHOOK_PORT", "8089"))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_recent(limit: int = 20) -> dict:
    """Read recent WhatsApp task files from the vault."""
    messages = []
    for f in sorted(NEEDS_ACTION.glob("WHATSAPP_*.md"), reverse=True)[:limit]:
        try:
            content = f.read_text(encoding="utf-8")
            meta = {"filename": f.name}
            # Parse YAML frontmatter
            lines = content.splitlines()
            if lines and lines[0].strip() == "---":
                for line in lines[1:]:
                    if line.strip() == "---":
                        break
                    if ":" in line:
                        k, _, v = line.partition(":")
                        meta[k.strip()] = v.strip()
            messages.append(meta)
        except Exception:
            pass
    return {"count": len(messages), "messages": messages}


def _draft_send_message(to: str, text: str) -> dict:
    """Create a Pending_Approval file for a WhatsApp message. Does NOT send."""
    # Rate limiting — max 5 WhatsApp drafts per hour
    try:
        get_limiter(VAULT_PATH).check("whatsapp_send")
    except RateLimitExceededError as e:
        return {"error": str(e), "rate_limited": True}

    PENDING.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    ts  = now.strftime("%Y%m%dT%H%M%SZ")
    expires = (now + timedelta(hours=24)).isoformat()

    approval_file = PENDING / f"APPROVAL_whatsapp_{ts}.md"
    approval_file.write_text(
        f"""---
type: approval_request
action: whatsapp_send_message
to: {to}
created: {now.isoformat()}
expires: {expires}
status: pending
---

## WhatsApp Message Draft

**To:** {to}

**Message:**

{text}

---

## To Approve (send message)
Move this file to /Approved/

## To Reject (discard)
Move this file to /Rejected/
""",
        encoding="utf-8",
    )
    return {
        "result": "drafted",
        "approval_file": approval_file.name,
        "message": "Approval required before sending. Move file to /Approved/ to send.",
        "to": to,
        "preview": text[:100] + ("..." if len(text) > 100 else ""),
    }


def _get_status() -> dict:
    """Check WhatsApp webhook server and credential status."""
    import urllib.request
    import urllib.error

    creds_ok = bool(
        os.getenv("WHATSAPP_ACCESS_TOKEN")
        and os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    )
    webhook_live = False
    try:
        with urllib.request.urlopen(
            f"http://localhost:{WEBHOOK_PORT}/health", timeout=2
        ) as r:
            webhook_live = r.status == 200
    except Exception:
        pass

    pending_count = len(list(PENDING.glob("APPROVAL_whatsapp_*.md"))) if PENDING.exists() else 0
    received_count = len(list(NEEDS_ACTION.glob("WHATSAPP_*.md"))) if NEEDS_ACTION.exists() else 0

    return {
        "credentials_configured": creds_ok,
        "webhook_server_live": webhook_live,
        "webhook_port": WEBHOOK_PORT,
        "pending_approvals": pending_count,
        "messages_received_total": received_count,
    }


# ── MCP Server ────────────────────────────────────────────────────────────────

def main():
    """Run the WhatsApp MCP Server using stdio transport."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp import types
    except ImportError:
        sys.stderr.write("ERROR: mcp package not installed. Run: uv sync\n")
        raise SystemExit(1)

    server = Server("whatsapp-mcp")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="whatsapp_get_recent",
                description=(
                    "Read recent WhatsApp messages received via the webhook watcher. "
                    "Returns message metadata from WHATSAPP_*.md files in /Needs_Action/."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Max messages to return (default: 20)"},
                    },
                },
            ),
            types.Tool(
                name="whatsapp_send_message",
                description=(
                    "DRAFT a WhatsApp message for human approval. "
                    "Creates a Pending_Approval file — does NOT send immediately. "
                    "Move the approval file to /Approved/ to send. "
                    "Handbook §3: outbound messages always require approval."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to":   {"type": "string", "description": "Recipient phone number (E.164 format, e.g. +1234567890)"},
                        "text": {"type": "string", "description": "Message text to send"},
                    },
                    "required": ["to", "text"],
                },
            ),
            types.Tool(
                name="whatsapp_get_status",
                description=(
                    "Check WhatsApp webhook server status, credential configuration, "
                    "and counts of received messages and pending approvals."
                ),
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        if name == "whatsapp_get_recent":
            result = _get_recent(limit=arguments.get("limit", 20))
        elif name == "whatsapp_send_message":
            result = _draft_send_message(
                to=arguments["to"],
                text=arguments["text"],
            )
        elif name == "whatsapp_get_status":
            result = _get_status()
        else:
            result = {"error": f"Unknown tool: {name}"}

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
