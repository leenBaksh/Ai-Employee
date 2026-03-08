"""
slack_mcp_server.py — Slack MCP Server for the AI Employee.

Exposes four MCP tools to Claude:
  - list_channels()                          → list public channels
  - read_channel(channel, limit?)            → read recent messages
  - send_message(channel, text)              → draft in /Pending_Approval/ (HITL)
  - add_reaction(channel, timestamp, emoji)  → add emoji reaction (auto-allowed)

Security (Handbook §3):
  - Read tools (list_channels, read_channel, add_reaction) execute immediately
  - send_message ALWAYS creates an approval file — never posts directly
  - All actions logged to /Logs/

Setup:
  1. Go to https://api.slack.com/apps → Create App → From scratch
  2. Add Bot Token Scopes: channels:read, channels:history, chat:write, reactions:write
  3. Install app to workspace → copy Bot User OAuth Token
  Set in .env:
    SLACK_BOT_TOKEN=xoxb-your-token
    SLACK_WORKSPACE=your-workspace-name   # for display only

Run as MCP server (stdio transport):
    uv run slack-mcp
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from audit_logger import write_log_entry, infer_approval

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

VAULT_PATH       = Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()
SLACK_BOT_TOKEN  = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_WORKSPACE  = os.getenv("SLACK_WORKSPACE", "workspace")
DRY_RUN          = os.getenv("DRY_RUN", "true").lower() == "true"

LOGS_DIR         = VAULT_PATH / "Logs"
PENDING_DIR      = VAULT_PATH / "Pending_Approval"
DRAFTS_DIR       = VAULT_PATH / "Drafts"

for d in [LOGS_DIR, PENDING_DIR, DRAFTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

SLACK_API = "https://slack.com/api"


# ── Logging ───────────────────────────────────────────────────────────────────

def _log(action_type: str, target: str, result: str, details: dict = None):
    approval_status, approved_by = infer_approval(action_type, DRY_RUN)
    write_log_entry(
        logs_dir=LOGS_DIR,
        action_type=action_type,
        actor="slack_mcp_server",
        target=target,
        result=result,
        parameters=details or {},
        approval_status=approval_status,
        approved_by=approved_by,
    )


# ── Slack API calls (via httpx — already a project dep) ───────────────────────

async def _slack_get(endpoint: str, params: dict = None) -> dict:
    """Make an authenticated GET request to the Slack Web API."""
    try:
        import httpx
    except ImportError:
        raise ImportError("httpx not installed. Run: uv sync")

    if not SLACK_BOT_TOKEN:
        return {"ok": False, "error": "SLACK_BOT_TOKEN not set in .env"}

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            f"{SLACK_API}/{endpoint}",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            params=params or {},
        )
        return response.json()


async def _slack_post(endpoint: str, payload: dict) -> dict:
    """Make an authenticated POST request to the Slack Web API."""
    try:
        import httpx
    except ImportError:
        raise ImportError("httpx not installed. Run: uv sync")

    if not SLACK_BOT_TOKEN:
        return {"ok": False, "error": "SLACK_BOT_TOKEN not set in .env"}

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{SLACK_API}/{endpoint}",
            headers={
                "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        return response.json()


# ── Tools implementation ──────────────────────────────────────────────────────

async def _list_channels() -> dict:
    """List public channels in the workspace."""
    data = await _slack_get("conversations.list", {"exclude_archived": "true", "limit": "50"})
    if not data.get("ok"):
        _log("slack_list_channels", SLACK_WORKSPACE, "error", {"error": data.get("error")})
        return {"error": data.get("error", "Slack API error"), "channels": []}

    channels = [
        {
            "id":           ch.get("id"),
            "name":         ch.get("name"),
            "topic":        ch.get("topic", {}).get("value", ""),
            "member_count": ch.get("num_members", 0),
            "is_private":   ch.get("is_private", False),
        }
        for ch in data.get("channels", [])
    ]
    _log("slack_list_channels", SLACK_WORKSPACE, "success", {"count": len(channels)})
    return {"channels": channels, "count": len(channels)}


async def _read_channel(channel: str, limit: int = 20) -> dict:
    """Read recent messages from a channel."""
    data = await _slack_get("conversations.history", {"channel": channel, "limit": str(limit)})
    if not data.get("ok"):
        _log("slack_read_channel", channel, "error", {"error": data.get("error")})
        return {"error": data.get("error", "Slack API error"), "messages": []}

    messages = []
    for msg in data.get("messages", []):
        messages.append({
            "ts":   msg.get("ts"),
            "user": msg.get("user") or msg.get("bot_id", "bot"),
            "text": msg.get("text", "")[:500],  # truncate per Handbook §6
            "reactions": [r.get("name") for r in msg.get("reactions", [])],
        })

    _log("slack_read_channel", channel, "success", {"limit": limit, "returned": len(messages)})
    return {"channel": channel, "messages": messages, "count": len(messages)}


def _draft_send_message(channel: str, text: str) -> dict:
    """Create an approval file for a Slack message — never posts directly."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_ch = channel.replace("#", "").replace(" ", "_")[:30]
    approval_file = PENDING_DIR / f"APPROVAL_slack_message_{ts}_{safe_ch}.md"

    approval_file.write_text(
        f"""---
type: approval_request
action: send_slack_message
channel: {channel}
created: {datetime.now(timezone.utc).isoformat()}
status: pending
---

# [Slack] Send Message — Approval Required

**Channel:** {channel}

## Message Content

> {text}

## Instructions

- **Approve:** Move this file to `/Approved/`
- **Reject:** Move this file to `/Rejected/`
- Edit the message content above before approving if needed

---
*Drafted by Slack MCP · Handbook §3 — messages require human approval before sending*
""",
        encoding="utf-8",
    )

    _log("slack_draft_message", channel, "success", {"approval_file": approval_file.name})
    return {
        "success": True,
        "message": f"Slack message queued for approval: {approval_file.name}",
        "approval_file": approval_file.name,
        "channel": channel,
    }


async def _add_reaction(channel: str, timestamp: str, emoji: str) -> dict:
    """Add an emoji reaction to a message — auto-allowed (low-risk read-adjacent action)."""
    if DRY_RUN:
        _log("slack_add_reaction", channel, "dry_run", {"emoji": emoji, "ts": timestamp})
        return {"success": True, "dry_run": True, "message": f"[DRY RUN] Would add :{emoji}: to {timestamp}"}

    clean_emoji = emoji.strip(":")
    data = await _slack_post("reactions.add", {
        "channel":   channel,
        "timestamp": timestamp,
        "name":      clean_emoji,
    })

    result = "success" if data.get("ok") else "error"
    _log("slack_add_reaction", channel, result, {"emoji": clean_emoji, "ts": timestamp,
                                                   "error": data.get("error")})
    if data.get("ok"):
        return {"success": True, "emoji": clean_emoji, "channel": channel}
    return {"success": False, "error": data.get("error", "Slack API error")}


# ── MCP Server ────────────────────────────────────────────────────────────────

def main():
    """Run the Slack MCP Server using stdio transport."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp import types
    except ImportError:
        sys.stderr.write("ERROR: mcp package not installed. Run: uv sync\n")
        raise SystemExit(1)

    server = Server("slack-mcp")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="list_channels",
                description=(
                    "List public Slack channels in the workspace. "
                    "Read-only — executes immediately. Returns channel IDs, names, member counts."
                ),
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="read_channel",
                description=(
                    "Read recent messages from a Slack channel. "
                    "Read-only — executes immediately. Use channel ID (e.g. C012AB3CD) or #name."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string", "description": "Channel ID or #channel-name"},
                        "limit":   {"type": "integer", "description": "Number of messages (default 20, max 100)", "default": 20},
                    },
                    "required": ["channel"],
                },
            ),
            types.Tool(
                name="send_message",
                description=(
                    "Draft a Slack message for human approval before sending. "
                    "Creates an approval file in /Pending_Approval/ — does NOT post directly. "
                    "Handbook §3: all outbound messages require approval."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string", "description": "Channel ID or #channel-name"},
                        "text":    {"type": "string", "description": "Message text (supports Slack markdown)"},
                    },
                    "required": ["channel", "text"],
                },
            ),
            types.Tool(
                name="add_reaction",
                description=(
                    "Add an emoji reaction to a Slack message. "
                    "Low-risk action — executes immediately (no approval needed). "
                    "Use message timestamp from read_channel results."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel":   {"type": "string", "description": "Channel ID"},
                        "timestamp": {"type": "string", "description": "Message timestamp (ts field from read_channel)"},
                        "emoji":     {"type": "string", "description": "Emoji name without colons (e.g. 'thumbsup', 'white_check_mark')"},
                    },
                    "required": ["channel", "timestamp", "emoji"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        if name == "list_channels":
            result = await _list_channels()
        elif name == "read_channel":
            result = await _read_channel(
                channel=arguments["channel"],
                limit=arguments.get("limit", 20),
            )
        elif name == "send_message":
            result = _draft_send_message(
                channel=arguments["channel"],
                text=arguments["text"],
            )
        elif name == "add_reaction":
            result = await _add_reaction(
                channel=arguments["channel"],
                timestamp=arguments["timestamp"],
                emoji=arguments["emoji"],
            )
        else:
            result = {"error": f"Unknown tool: {name}"}

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
