"""
audit_mcp_server.py — Structured Audit MCP Server for the AI Employee.

Exposes 4 MCP tools to Claude:
  - audit_get_errors(days?, limit?)       → scan Logs/*.json for error entries
  - audit_get_activity_summary(days?)     → count actions by type/actor
  - audit_search_logs(keyword, days?)     → search logs by keyword or action_type
  - audit_get_weekly_report()             → structured 7-day business summary

Reads from: {VAULT_PATH}/Logs/YYYY-MM-DD.json
No external dependencies — stdlib json + pathlib only.

Run as MCP server (stdio transport):
    uv run audit-mcp

Configure in .claude/mcp.json:
    {
      "audit": {
        "command": "uv",
        "args": ["run", "--directory", ".", "audit-mcp"],
        "env": { "VAULT_PATH": "./AI_Employee_Vault" }
      }
    }
"""

import os
import re
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

VAULT_PATH = Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()
LOGS_DIR = VAULT_PATH / "Logs"


def _load_logs(days: int = 7) -> list[dict]:
    """Load log entries from the last N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    entries = []
    if not LOGS_DIR.exists():
        return entries
    for log_file in sorted(LOGS_DIR.glob("*.json")):
        try:
            # Parse date from filename (YYYY-MM-DD.json)
            file_date = datetime.strptime(log_file.stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if file_date < cutoff - timedelta(days=1):
                continue
            raw = json.loads(log_file.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                entries.extend(raw)
        except Exception:
            pass
    return entries


def _get_errors(days: int = 7, limit: int = 50) -> dict:
    """Scan logs for error-level entries."""
    entries = _load_logs(days)
    errors = [
        e for e in entries
        if str(e.get("result", "")).lower() in ("error", "warning", "breach_detected")
        or "error" in str(e.get("result", "")).lower()
    ]
    errors.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return {
        "total_errors": len(errors),
        "days_scanned": days,
        "errors": errors[:limit],
    }


def _get_activity_summary(days: int = 7) -> dict:
    """Count actions by type and actor."""
    entries = _load_logs(days)
    by_type: dict[str, int] = {}
    by_actor: dict[str, int] = {}
    by_result: dict[str, int] = {}

    for e in entries:
        action = e.get("action_type", "unknown")
        actor = e.get("actor", "unknown")
        result = e.get("result", "unknown")
        by_type[action] = by_type.get(action, 0) + 1
        by_actor[actor] = by_actor.get(actor, 0) + 1
        by_result[result] = by_result.get(result, 0) + 1

    # Sort by count desc
    by_type = dict(sorted(by_type.items(), key=lambda x: x[1], reverse=True))
    by_actor = dict(sorted(by_actor.items(), key=lambda x: x[1], reverse=True))

    return {
        "total_entries": len(entries),
        "days": days,
        "by_action_type": by_type,
        "by_actor": by_actor,
        "by_result": by_result,
    }


def _search_logs(keyword: str, days: int = 7) -> dict:
    """Search log entries by keyword (checks action_type, target, result, parameters)."""
    entries = _load_logs(days)
    keyword_lower = keyword.lower()
    matches = []
    for e in entries:
        searchable = json.dumps(e).lower()
        if keyword_lower in searchable:
            matches.append(e)
    matches.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return {
        "keyword": keyword,
        "days_scanned": days,
        "match_count": len(matches),
        "matches": matches[:100],
    }


def _get_weekly_report() -> dict:
    """Produce a structured 7-day business summary."""
    entries = _load_logs(7)
    now = datetime.now(timezone.utc)

    # Counts
    total = len(entries)
    errors = [e for e in entries if "error" in str(e.get("result", "")).lower()]
    successes = [e for e in entries if str(e.get("result", "")).lower() in ("success", "notified", "in_progress")]

    # Top action types
    by_type: dict[str, int] = {}
    for e in entries:
        t = e.get("action_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    top_actions = sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:10]

    # Vault health
    needs_action_count = len(list((VAULT_PATH / "Needs_Action").glob("*.md"))) if (VAULT_PATH / "Needs_Action").exists() else 0
    pending_count = len(list((VAULT_PATH / "Pending_Approval").glob("*.md"))) if (VAULT_PATH / "Pending_Approval").exists() else 0
    done_count = len(list((VAULT_PATH / "Done").glob("*"))) if (VAULT_PATH / "Done").exists() else 0

    return {
        "report_generated": now.isoformat(),
        "period": {
            "start": (now - timedelta(days=7)).strftime("%Y-%m-%d"),
            "end": now.strftime("%Y-%m-%d"),
        },
        "activity": {
            "total_log_entries": total,
            "successes": len(successes),
            "errors": len(errors),
            "error_rate_pct": round(len(errors) / total * 100, 1) if total else 0,
        },
        "top_actions": [{"action": a, "count": c} for a, c in top_actions],
        "recent_errors": errors[-5:] if errors else [],
        "vault_health": {
            "needs_action": needs_action_count,
            "pending_approval": pending_count,
            "done_total": done_count,
        },
    }


# ── MCP Server ────────────────────────────────────────────────────────────────
def main():
    """Run the Audit MCP Server using stdio transport."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp import types
    except ImportError:
        print("ERROR: mcp package not installed. Run: uv sync")
        raise SystemExit(1)

    server = Server("audit-mcp")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="audit_get_errors",
                description="Scan Logs/*.json for error-level entries. Returns top N errors sorted newest-first.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days":  {"type": "integer", "description": "How many days back to scan (default: 7)"},
                        "limit": {"type": "integer", "description": "Max errors to return (default: 50)"},
                    },
                },
            ),
            types.Tool(
                name="audit_get_activity_summary",
                description="Count log entries by action_type and actor for the given period.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days": {"type": "integer", "description": "How many days back to summarize (default: 7)"},
                    },
                },
            ),
            types.Tool(
                name="audit_search_logs",
                description="Search log entries by keyword. Searches action_type, target, result, and parameters.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string", "description": "Search term"},
                        "days":    {"type": "integer", "description": "How many days back to search (default: 7)"},
                    },
                    "required": ["keyword"],
                },
            ),
            types.Tool(
                name="audit_get_weekly_report",
                description="Generate a structured 7-day business summary: activity stats, error rate, vault health, top actions.",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        if name == "audit_get_errors":
            result = _get_errors(
                days=arguments.get("days", 7),
                limit=arguments.get("limit", 50),
            )
        elif name == "audit_get_activity_summary":
            result = _get_activity_summary(days=arguments.get("days", 7))
        elif name == "audit_search_logs":
            result = _search_logs(
                keyword=arguments["keyword"],
                days=arguments.get("days", 7),
            )
        elif name == "audit_get_weekly_report":
            result = _get_weekly_report()
        else:
            result = {"error": f"Unknown tool: {name}"}

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
