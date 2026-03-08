"""
calendar_mcp_server.py — Google Calendar MCP Server for the AI Employee.

Exposes four MCP tools to Claude:
  - list_events(days_ahead?)         → upcoming events from primary calendar
  - create_event(summary, start, end, description?, attendees?)
                                     → draft in /Pending_Approval/ (HITL)
  - update_event(event_id, ...)      → draft update in /Pending_Approval/
  - delete_event(event_id, reason?)  → draft deletion in /Pending_Approval/

Security (Handbook §3):
  - Read-only tools (list_events) execute immediately
  - Write tools (create/update/delete) ALWAYS create approval files — never execute directly
  - All actions logged to /Logs/

Setup:
  Uses the same Google OAuth token as Gmail watcher (gmail_token.json).
  Set in .env:
    GMAIL_TOKEN_PATH=./secrets/gmail_token.json
    GOOGLE_CALENDAR_ID=primary           # or a specific calendar ID

Run as MCP server (stdio transport):
    uv run calendar-mcp
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from audit_logger import write_log_entry, infer_approval

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

VAULT_PATH   = Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()
GMAIL_TOKEN  = os.getenv("GMAIL_TOKEN_PATH", "./secrets/gmail_token.json")
CALENDAR_ID  = os.getenv("GOOGLE_CALENDAR_ID", "primary")
DRY_RUN      = os.getenv("DRY_RUN", "true").lower() == "true"

LOGS_DIR     = VAULT_PATH / "Logs"
PENDING_DIR  = VAULT_PATH / "Pending_Approval"

for d in [LOGS_DIR, PENDING_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ── Logging ───────────────────────────────────────────────────────────────────

def _log(action_type: str, target: str, result: str, details: dict = None):
    approval_status, approved_by = infer_approval(action_type, DRY_RUN)
    write_log_entry(
        logs_dir=LOGS_DIR,
        action_type=action_type,
        actor="calendar_mcp_server",
        target=target,
        result=result,
        parameters=details or {},
        approval_status=approval_status,
        approved_by=approved_by,
    )


# ── Google Calendar client ────────────────────────────────────────────────────

def _get_calendar_service():
    """Build an authenticated Google Calendar API service using the Gmail token."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError("Google API dependencies not installed. Run: uv sync")

    token_path = Path(GMAIL_TOKEN)
    if not token_path.exists():
        raise FileNotFoundError(
            f"Google token not found at {token_path}. "
            "Run: uv run gmail-watcher --setup"
        )

    creds = Credentials.from_authorized_user_file(
        str(token_path),
        scopes=[
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/gmail.readonly",
        ],
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("calendar", "v3", credentials=creds)


# ── Tools implementation ──────────────────────────────────────────────────────

def _list_events(days_ahead: int = 7) -> dict:
    """Return upcoming events from the primary calendar."""
    try:
        service = _get_calendar_service()
        now = datetime.now(timezone.utc)
        time_max = now + timedelta(days=days_ahead)

        result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=now.isoformat(),
            timeMax=time_max.isoformat(),
            maxResults=20,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = []
        for e in result.get("items", []):
            start = e.get("start", {})
            events.append({
                "id":          e.get("id"),
                "summary":     e.get("summary", "(No title)"),
                "start":       start.get("dateTime") or start.get("date"),
                "end":         (e.get("end", {}).get("dateTime") or e.get("end", {}).get("date")),
                "description": e.get("description", ""),
                "attendees":   [a.get("email") for a in e.get("attendees", [])],
                "status":      e.get("status"),
            })

        _log("calendar_list_events", CALENDAR_ID, "success", {"days_ahead": days_ahead, "count": len(events)})
        return {"events": events, "count": len(events), "period_days": days_ahead}

    except Exception as e:
        _log("calendar_list_events", CALENDAR_ID, "error", {"error": str(e)})
        return {"error": str(e), "events": []}


def _draft_create_event(summary: str, start: str, end: str,
                         description: str = "", attendees: str = "") -> dict:
    """Create an approval file for a new calendar event — never auto-creates."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in summary)[:40]
    approval_file = PENDING_DIR / f"APPROVAL_calendar_create_{ts}_{safe}.md"

    approval_file.write_text(
        f"""---
type: approval_request
action: create_calendar_event
calendar_id: {CALENDAR_ID}
summary: {summary}
start: {start}
end: {end}
attendees: {attendees}
created: {datetime.now(timezone.utc).isoformat()}
status: pending
---

# [Calendar] Create Event — Approval Required

## Event Details

| Field | Value |
|-------|-------|
| Title | {summary} |
| Start | {start} |
| End   | {end} |
| Attendees | {attendees or '(none)'} |

## Description

{description or '(none)'}

## Instructions

- **Approve:** Move this file to `/Approved/`
- **Reject:** Move this file to `/Rejected/`

---
*Drafted by Calendar MCP · Handbook §3 — write actions require approval*
""",
        encoding="utf-8",
    )

    _log("calendar_draft_create", summary, "success", {
        "start": start, "end": end, "approval_file": approval_file.name
    })
    return {
        "success": True,
        "message": f"Event creation queued for approval: {approval_file.name}",
        "approval_file": approval_file.name,
    }


def _draft_update_event(event_id: str, summary: str = "", start: str = "",
                         end: str = "", description: str = "") -> dict:
    """Create an approval file to update an existing event."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    approval_file = PENDING_DIR / f"APPROVAL_calendar_update_{ts}_{event_id[:12]}.md"

    changes = {k: v for k, v in
               {"summary": summary, "start": start, "end": end, "description": description}.items() if v}

    approval_file.write_text(
        f"""---
type: approval_request
action: update_calendar_event
event_id: {event_id}
created: {datetime.now(timezone.utc).isoformat()}
status: pending
---

# [Calendar] Update Event — Approval Required

**Event ID:** `{event_id}`

## Proposed Changes

{chr(10).join(f'- **{k}:** {v}' for k, v in changes.items()) or '(no changes specified)'}

## Instructions

- **Approve:** Move this file to `/Approved/`
- **Reject:** Move this file to `/Rejected/`

---
*Drafted by Calendar MCP · Handbook §3 — write actions require approval*
""",
        encoding="utf-8",
    )

    _log("calendar_draft_update", event_id, "success", {"approval_file": approval_file.name})
    return {
        "success": True,
        "message": f"Event update queued for approval: {approval_file.name}",
        "approval_file": approval_file.name,
    }


def _draft_delete_event(event_id: str, reason: str = "") -> dict:
    """Create an approval file to delete an event."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    approval_file = PENDING_DIR / f"APPROVAL_calendar_delete_{ts}_{event_id[:12]}.md"

    approval_file.write_text(
        f"""---
type: approval_request
action: delete_calendar_event
event_id: {event_id}
reason: {reason}
created: {datetime.now(timezone.utc).isoformat()}
status: pending
---

# [Calendar] Delete Event — Approval Required

**Event ID:** `{event_id}`
**Reason:** {reason or '(not specified)'}

⚠️ This action is irreversible. Confirm before approving.

## Instructions

- **Approve:** Move this file to `/Approved/`
- **Reject:** Move this file to `/Rejected/`

---
*Drafted by Calendar MCP · Handbook §3 — delete actions require approval*
""",
        encoding="utf-8",
    )

    _log("calendar_draft_delete", event_id, "success", {"approval_file": approval_file.name})
    return {
        "success": True,
        "message": f"Event deletion queued for approval: {approval_file.name}",
        "approval_file": approval_file.name,
    }


# ── MCP Server ────────────────────────────────────────────────────────────────

def main():
    """Run the Calendar MCP Server using stdio transport."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp import types
    except ImportError:
        sys.stderr.write("ERROR: mcp package not installed. Run: uv sync\n")
        raise SystemExit(1)

    server = Server("calendar-mcp")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="list_events",
                description=(
                    "List upcoming Google Calendar events. Safe read-only operation — executes immediately. "
                    "Returns event IDs, titles, times, attendees for the next N days."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days_ahead": {
                            "type": "integer",
                            "description": "How many days ahead to fetch (default: 7)",
                            "default": 7,
                        },
                    },
                },
            ),
            types.Tool(
                name="create_event",
                description=(
                    "Draft a new calendar event for human approval. "
                    "Creates an approval file in /Pending_Approval/ — does NOT create the event directly. "
                    "Dates must be ISO 8601 format: 2026-03-10T14:00:00+02:00"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "summary":     {"type": "string", "description": "Event title"},
                        "start":       {"type": "string", "description": "Start datetime (ISO 8601)"},
                        "end":         {"type": "string", "description": "End datetime (ISO 8601)"},
                        "description": {"type": "string", "description": "Event description (optional)"},
                        "attendees":   {"type": "string", "description": "Comma-separated email list (optional)"},
                    },
                    "required": ["summary", "start", "end"],
                },
            ),
            types.Tool(
                name="update_event",
                description=(
                    "Draft an update to an existing calendar event for human approval. "
                    "Only provide fields you want to change."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "event_id":    {"type": "string", "description": "Google Calendar event ID"},
                        "summary":     {"type": "string", "description": "New event title (optional)"},
                        "start":       {"type": "string", "description": "New start datetime ISO 8601 (optional)"},
                        "end":         {"type": "string", "description": "New end datetime ISO 8601 (optional)"},
                        "description": {"type": "string", "description": "New description (optional)"},
                    },
                    "required": ["event_id"],
                },
            ),
            types.Tool(
                name="delete_event",
                description=(
                    "Draft a calendar event deletion for human approval. "
                    "Creates approval file — does NOT delete immediately. Irreversible action."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "event_id": {"type": "string", "description": "Google Calendar event ID"},
                        "reason":   {"type": "string", "description": "Reason for deletion (optional)"},
                    },
                    "required": ["event_id"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        if name == "list_events":
            result = _list_events(days_ahead=arguments.get("days_ahead", 7))
        elif name == "create_event":
            result = _draft_create_event(
                summary=arguments["summary"],
                start=arguments["start"],
                end=arguments["end"],
                description=arguments.get("description", ""),
                attendees=arguments.get("attendees", ""),
            )
        elif name == "update_event":
            result = _draft_update_event(
                event_id=arguments["event_id"],
                summary=arguments.get("summary", ""),
                start=arguments.get("start", ""),
                end=arguments.get("end", ""),
                description=arguments.get("description", ""),
            )
        elif name == "delete_event":
            result = _draft_delete_event(
                event_id=arguments["event_id"],
                reason=arguments.get("reason", ""),
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
