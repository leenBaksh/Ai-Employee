"""
gmail_mcp_server.py — Gmail MCP Server for the AI Employee.

Exposes 3 MCP tools to Claude:
  - gmail_get_recent(max_results?, label?)  → list recent emails
  - gmail_search(query, max_results?)       → search Gmail inbox
  - gmail_send_draft(to, subject, body)     → HITL: creates Drafts/ + Pending_Approval file

Reuses the OAuth token from gmail_token.json (same credential as gmail_watcher.py).
No new OAuth setup required.

Run as MCP server (stdio transport):
    uv run gmail-mcp

Configure in .claude/mcp.json:
    {
      "gmail": {
        "command": "uv",
        "args": ["run", "--directory", ".", "gmail-mcp"],
        "env": { "VAULT_PATH": "./AI_Employee_Vault" }
      }
    }
"""

import os
import json
import base64
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

VAULT_PATH       = Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()
TOKEN_PATH       = Path(os.getenv("GMAIL_TOKEN_PATH", "./secrets/gmail_token.json"))
CREDENTIALS_PATH = Path(os.getenv("GMAIL_CREDENTIALS_PATH", "./secrets/gmail_credentials.json"))
PENDING          = VAULT_PATH / "Pending_Approval"
DRAFTS           = VAULT_PATH / "Drafts"

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

MAX_BODY_CHARS = 500  # truncate long email bodies for privacy


# ── Gmail API helpers ─────────────────────────────────────────────────────────

def _build_gmail_service():
    """Build authenticated Gmail API service. Returns None if credentials missing."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        if not TOKEN_PATH.exists():
            return None, "gmail_token.json not found. Run gmail-watcher --setup first."

        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), GMAIL_SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

        return build("gmail", "v1", credentials=creds, cache_discovery=False), None
    except Exception as e:
        return None, str(e)


def _parse_message(msg: dict) -> dict:
    """Extract key fields from a Gmail message resource."""
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    snippet = msg.get("snippet", "")[:MAX_BODY_CHARS]
    return {
        "id":      msg.get("id"),
        "date":    headers.get("date", ""),
        "from":    headers.get("from", ""),
        "to":      headers.get("to", ""),
        "subject": headers.get("subject", "(no subject)"),
        "snippet": snippet,
        "labels":  msg.get("labelIds", []),
    }


def _get_recent(max_results: int = 10, label: str = "INBOX") -> dict:
    service, err = _build_gmail_service()
    if err:
        return {"error": err}
    try:
        resp = service.users().messages().list(
            userId="me", labelIds=[label.upper()], maxResults=max_results
        ).execute()
        messages = []
        for m in resp.get("messages", []):
            full = service.users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date"]
            ).execute()
            messages.append(_parse_message(full))
        return {
            "label": label,
            "count": len(messages),
            "messages": messages,
        }
    except Exception as e:
        return {"error": str(e)}


def _search(query: str, max_results: int = 10) -> dict:
    service, err = _build_gmail_service()
    if err:
        return {"error": err}
    try:
        resp = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        messages = []
        for m in resp.get("messages", []):
            full = service.users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date"]
            ).execute()
            messages.append(_parse_message(full))
        return {
            "query": query,
            "count": len(messages),
            "messages": messages,
        }
    except Exception as e:
        return {"error": str(e)}


def _draft_send(to: str, subject: str, body: str) -> dict:
    """Save a draft to Drafts/ and create a Pending_Approval file. Does NOT send."""
    DRAFTS.mkdir(parents=True, exist_ok=True)
    PENDING.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    ts  = now.strftime("%Y%m%dT%H%M%SZ")
    expires = (now + timedelta(hours=24)).isoformat()
    safe_subj = subject[:40].replace(" ", "_").replace("/", "_")

    draft_file = DRAFTS / f"EMAIL_DRAFT_{ts}_{safe_subj}.md"
    draft_file.write_text(
        f"""---
type: email_draft
to: {to}
subject: {subject}
created: {now.isoformat()}
status: draft
---

## To
{to}

## Subject
{subject}

## Body

{body}
""",
        encoding="utf-8",
    )

    approval_file = PENDING / f"APPROVAL_email_{ts}_{safe_subj}.md"
    approval_file.write_text(
        f"""---
type: approval_request
action: send_email
to: {to}
subject: {subject}
draft_file: {draft_file.name}
created: {now.isoformat()}
expires: {expires}
status: pending
---

## Email Draft Ready to Send

**To:** {to}
**Subject:** {subject}

**Preview:**
{body[:200]}{"..." if len(body) > 200 else ""}

Full draft: `Drafts/{draft_file.name}`

## To Approve (send email)
Move this file to /Approved/

## To Reject (discard)
Move this file to /Rejected/
""",
        encoding="utf-8",
    )

    return {
        "result": "drafted",
        "draft_file": draft_file.name,
        "approval_file": approval_file.name,
        "message": "Email drafted. Move approval file to /Approved/ to send.",
    }


# ── MCP Server ────────────────────────────────────────────────────────────────

def main():
    """Run the Gmail MCP Server using stdio transport."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp import types
    except ImportError:
        sys.stderr.write("ERROR: mcp package not installed. Run: uv sync\n")
        raise SystemExit(1)

    server = Server("gmail-mcp")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="gmail_get_recent",
                description=(
                    "List recent emails from Gmail. "
                    "Returns subject, sender, date, and snippet (first 500 chars). "
                    "Reuses existing gmail_token.json — no new auth needed."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "max_results": {"type": "integer", "description": "Max emails to return (default: 10)"},
                        "label":       {"type": "string",  "description": "Gmail label to read (default: INBOX). Options: INBOX, IMPORTANT, UNREAD, SENT"},
                    },
                },
            ),
            types.Tool(
                name="gmail_search",
                description=(
                    "Search Gmail using Gmail query syntax. "
                    "Examples: 'from:client@example.com', 'subject:invoice', 'is:unread'. "
                    "Returns matching messages with subject, sender, date, snippet."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query":       {"type": "string",  "description": "Gmail search query"},
                        "max_results": {"type": "integer", "description": "Max results (default: 10)"},
                    },
                    "required": ["query"],
                },
            ),
            types.Tool(
                name="gmail_send_draft",
                description=(
                    "DRAFT an email for human approval. "
                    "Saves to /Drafts/ and creates a Pending_Approval file. "
                    "Does NOT send immediately. "
                    "Handbook §3: outbound emails always require approval."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to":      {"type": "string", "description": "Recipient email address"},
                        "subject": {"type": "string", "description": "Email subject line"},
                        "body":    {"type": "string", "description": "Email body (plain text or markdown)"},
                    },
                    "required": ["to", "subject", "body"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        if name == "gmail_get_recent":
            result = _get_recent(
                max_results=arguments.get("max_results", 10),
                label=arguments.get("label", "INBOX"),
            )
        elif name == "gmail_search":
            result = _search(
                query=arguments["query"],
                max_results=arguments.get("max_results", 10),
            )
        elif name == "gmail_send_draft":
            result = _draft_send(
                to=arguments["to"],
                subject=arguments["subject"],
                body=arguments["body"],
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
