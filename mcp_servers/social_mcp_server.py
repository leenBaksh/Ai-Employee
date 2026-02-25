"""
social_mcp_server.py — Unified Social Media MCP Server for the AI Employee.

Handles Facebook, Instagram, and Twitter using the same draft/approval pattern
as email_mcp_server.py. Actual posting is done via Playwright MCP browser automation
(same pattern as LinkedIn) after human approval.

Exposes 4 MCP tools to Claude:
  - social_draft_post(platform, content, media_url?)  → save to /To_Post/<Platform>/
  - social_check_limits(platform)                     → remaining posts today
  - social_get_summary()                              → counts per platform
  - social_list_pending(platform?)                    → list unapproved drafts

Platforms: Facebook, Instagram, Twitter

Run as MCP server (stdio transport):
    uv run social-mcp

Security:
  - NEVER posts directly — always creates a draft + approval request
  - Enforces daily post limits per platform
  - All actions logged to /Logs/
"""

import os
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone, date
from dotenv import load_dotenv

load_dotenv()

VAULT_PATH = Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()
LOGS_DIR   = VAULT_PATH / "Logs"
TO_POST    = VAULT_PATH / "To_Post"
PENDING    = VAULT_PATH / "Pending_Approval"

PLATFORMS = ["Facebook", "Instagram", "Twitter"]

DAILY_LIMITS = {
    "Facebook":  int(os.getenv("FACEBOOK_MAX_POSTS_PER_DAY", "2")),
    "Instagram": int(os.getenv("INSTAGRAM_MAX_POSTS_PER_DAY", "2")),
    "Twitter":   int(os.getenv("TWITTER_MAX_POSTS_PER_DAY", "5")),
}

# State file for tracking daily post counts
_STATE_FILE = VAULT_PATH / ".social_posts_today.json"


def _log(action_type: str, target: str, result: str, details: dict = None):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action_type": action_type,
        "actor": "social_mcp_server",
        "target": target,
        "parameters": details or {},
        "result": result,
    }
    entries = []
    if log_file.exists():
        try:
            entries = json.loads(log_file.read_text(encoding="utf-8"))
        except Exception:
            entries = []
    entries.append(entry)
    log_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def _load_state() -> dict:
    """Load daily post counts, resetting if date has changed."""
    today = date.today().isoformat()
    if _STATE_FILE.exists():
        try:
            state = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
            if state.get("date") == today:
                return state
        except Exception:
            pass
    # Reset for today
    return {"date": today, "posts": {p: 0 for p in PLATFORMS}}


def _save_state(state: dict):
    _STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _ensure_dirs():
    for platform in PLATFORMS:
        (TO_POST / platform).mkdir(parents=True, exist_ok=True)
    PENDING.mkdir(parents=True, exist_ok=True)


def tool_draft_post(platform: str, content: str, media_url: str = "") -> dict:
    """Save a draft post and create an approval request."""
    _ensure_dirs()

    if platform not in PLATFORMS:
        return {"error": f"Unknown platform '{platform}'. Supported: {PLATFORMS}"}

    # Check daily limits
    state = _load_state()
    posts_today = state["posts"].get(platform, 0)
    limit = DAILY_LIMITS[platform]
    if posts_today >= limit:
        return {
            "error": f"{platform}: daily limit reached ({posts_today}/{limit} posts). Try again tomorrow.",
            "posts_today": posts_today,
            "limit": limit,
        }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_platform = platform.lower()

    # Save post content to /To_Post/<Platform>/
    post_file = TO_POST / platform / f"POST_{timestamp}_{safe_platform}.md"
    post_file.write_text(
        f"""---
type: social_post
platform: {platform}
status: draft
created: {datetime.now(timezone.utc).isoformat()}
media_url: {media_url}
---

## {platform} Post Draft

{content}

---
*AI-drafted post. Review before publishing.*
*Approve: move approval file from /Pending_Approval/ to /Approved/*
""",
        encoding="utf-8",
    )

    # Create approval request
    approval_file = PENDING / f"SOCIAL_{platform.upper()}_{timestamp}.md"
    approval_file.write_text(
        f"""---
type: social_post_approval
platform: {platform}
action: post_{safe_platform}
post_file: To_Post/{platform}/{post_file.name}
created: {datetime.now(timezone.utc).isoformat()}
status: pending_approval
expires: {datetime.now(timezone.utc).replace(hour=23, minute=59).isoformat()}
---

# Approval Required: {platform} Post

**Platform:** {platform}
**Post File:** `To_Post/{platform}/{post_file.name}`

## Post Content Preview

{content[:500]}{"..." if len(content) > 500 else ""}

## Actions

- **Approve:** Move this file to `/Approved/`
- **Reject:** Move this file to `/Rejected/`

---
*Human approval required before any social media posting (Company Handbook §4).*
""",
        encoding="utf-8",
    )

    _log("social_draft_post", platform, "success", {
        "post_file": post_file.name,
        "approval_file": approval_file.name,
        "content_length": len(content),
    })

    return {
        "success": True,
        "platform": platform,
        "post_file": str(post_file.relative_to(VAULT_PATH)),
        "approval_file": approval_file.name,
        "message": f"Draft saved. Approval required before posting to {platform}.",
        "posts_today": posts_today,
        "remaining_today": limit - posts_today,
    }


def tool_check_limits(platform: str = "") -> dict:
    """Return remaining post slots for today."""
    state = _load_state()
    if platform:
        if platform not in PLATFORMS:
            return {"error": f"Unknown platform: {platform}"}
        posts = state["posts"].get(platform, 0)
        limit = DAILY_LIMITS[platform]
        return {
            "platform": platform,
            "posts_today": posts,
            "limit": limit,
            "remaining": max(0, limit - posts),
            "date": state["date"],
        }
    # All platforms
    result = {"date": state["date"], "platforms": {}}
    for p in PLATFORMS:
        posts = state["posts"].get(p, 0)
        limit = DAILY_LIMITS[p]
        result["platforms"][p] = {
            "posts_today": posts,
            "limit": limit,
            "remaining": max(0, limit - posts),
        }
    return result


def tool_get_summary() -> dict:
    """Count pending and published posts per platform."""
    _ensure_dirs()
    state = _load_state()
    summary = {}
    for platform in PLATFORMS:
        pending_drafts = list((TO_POST / platform).glob("POST_*.md"))
        pending_approvals = list(PENDING.glob(f"SOCIAL_{platform.upper()}_*.md"))
        summary[platform] = {
            "drafts_in_queue": len(pending_drafts),
            "pending_approval": len(pending_approvals),
            "posts_today": state["posts"].get(platform, 0),
            "daily_limit": DAILY_LIMITS[platform],
        }
    return {"summary": summary, "date": state["date"]}


def tool_list_pending(platform: str = "") -> dict:
    """List unapproved social media drafts."""
    _ensure_dirs()
    results = []
    platforms_to_check = [platform] if platform and platform in PLATFORMS else PLATFORMS
    for p in platforms_to_check:
        for f in sorted((TO_POST / p).glob("POST_*.md")):
            try:
                content = f.read_text(encoding="utf-8")
                # Extract first non-frontmatter content line
                lines = [l for l in content.split("\n") if l and not l.startswith("---") and not l.startswith("#") and not l.startswith("*")]
                preview = lines[0][:100] if lines else ""
                results.append({
                    "platform": p,
                    "file": f.name,
                    "path": str(f.relative_to(VAULT_PATH)),
                    "preview": preview,
                })
            except Exception:
                results.append({"platform": p, "file": f.name})
    return {"pending_posts": results, "count": len(results)}


# ── MCP Server ────────────────────────────────────────────────────────────────
def main():
    """Run the Social MCP Server using stdio transport."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp import types
    except ImportError:
        print("ERROR: mcp package not installed. Run: uv sync")
        raise SystemExit(1)

    server = Server("social-mcp")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="social_draft_post",
                description=(
                    "Draft a social media post for Facebook, Instagram, or Twitter. "
                    "Saves to /To_Post/<Platform>/ and creates an approval request. "
                    "Handbook §4: NEVER posts directly — human approval required."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "platform":  {"type": "string", "description": "Facebook | Instagram | Twitter"},
                        "content":   {"type": "string", "description": "Post text content"},
                        "media_url": {"type": "string", "description": "Optional image/video URL"},
                    },
                    "required": ["platform", "content"],
                },
            ),
            types.Tool(
                name="social_check_limits",
                description="Check remaining post slots for today. Respects per-platform daily limits.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "platform": {"type": "string", "description": "Facebook | Instagram | Twitter (optional — omit for all)"},
                    },
                },
            ),
            types.Tool(
                name="social_get_summary",
                description="Get counts of pending/published posts per platform for today.",
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="social_list_pending",
                description="List all draft posts awaiting human approval.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "platform": {"type": "string", "description": "Filter by platform (optional)"},
                    },
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        if name == "social_draft_post":
            result = tool_draft_post(
                platform=arguments["platform"],
                content=arguments["content"],
                media_url=arguments.get("media_url", ""),
            )
        elif name == "social_check_limits":
            result = tool_check_limits(platform=arguments.get("platform", ""))
        elif name == "social_get_summary":
            result = tool_get_summary()
        elif name == "social_list_pending":
            result = tool_list_pending(platform=arguments.get("platform", ""))
        else:
            result = {"error": f"Unknown tool: {name}"}

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
