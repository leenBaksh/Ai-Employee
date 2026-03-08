"""
banking_mcp_server.py — Banking MCP Server for the AI Employee.

Exposes 4 MCP tools to Claude:
  - banking_get_transactions(days?, category?, type?)   → read from Bank_Transactions.md
  - banking_add_transaction(date, description, amount, type, category) → append to ledger
  - banking_get_summary()                               → MTD income/expenses/net/progress
  - banking_get_subscription_report()                   → run full subscription audit

Reads/writes: {VAULT_PATH}/Accounting/Bank_Transactions.md
Also delegates subscription audit to audit_logic.run_subscription_audit()

Run as MCP server (stdio transport):
    uv run banking-mcp

Configure in .claude/mcp.json:
    {
      "banking": {
        "command": "uv",
        "args": ["run", "--directory", ".", "banking-mcp"],
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
from audit_logic import run_subscription_audit, _parse_ledger_rows
from rate_limiter import get_limiter, RateLimitExceededError
from permission_guard import check as permission_check, add_known_payee

load_dotenv()

VAULT_PATH   = Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()
BANK_FILE    = VAULT_PATH / "Accounting" / "Bank_Transactions.md"
MONTH_FILE   = VAULT_PATH / "Accounting" / "Current_Month.md"
PENDING_DIR  = VAULT_PATH / "Pending_Approval"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _read_bank_file() -> str:
    if not BANK_FILE.exists():
        return ""
    return BANK_FILE.read_text(encoding="utf-8")


def _get_transactions(days: int = 90, category: str = "", tx_type: str = "") -> dict:
    """Parse ledger rows and apply optional filters."""
    content = _read_bank_file()
    if not content:
        return {"error": "Bank_Transactions.md not found"}

    rows = _parse_ledger_rows(content)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    filtered = []
    for row in rows:
        try:
            row_date = datetime.strptime(row["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if row_date < cutoff:
            continue
        if category and category.lower() not in row.get("category", "").lower():
            continue
        if tx_type and tx_type.lower() not in row.get("type", "").lower():
            continue
        filtered.append(row)

    total_income   = sum(r["amount"] for r in filtered if r["amount"] > 0)
    total_expenses = sum(r["amount"] for r in filtered if r["amount"] < 0)

    return {
        "days": days,
        "filters": {"category": category or None, "type": tx_type or None},
        "count": len(filtered),
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "net": round(total_income + total_expenses, 2),
        "transactions": filtered,
    }


def _add_transaction(
    date: str, description: str, amount: float, tx_type: str, category: str
) -> dict:
    """
    Append a new row to the Running Ledger table in Bank_Transactions.md.
    amount: positive for income, negative for expenses (e.g. -54.99).
    """
    content = _read_bank_file()
    if not content:
        return {"error": "Bank_Transactions.md not found"}

    # Validate date
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return {"error": f"Invalid date format '{date}'. Use YYYY-MM-DD."}

    sign = "+" if amount >= 0 else ""
    amount_str = f"{sign}${abs(amount):.2f}" if amount >= 0 else f"-${abs(amount):.2f}"
    new_row = f"| {date} | {description} | {amount_str} | {tx_type} | {category} | pending |"

    # Insert after the table header row (| Date | Description | ...)
    lines = content.splitlines()
    insert_at = None
    in_ledger = False
    for i, line in enumerate(lines):
        if line.startswith("## Running Ledger"):
            in_ledger = True
            continue
        if in_ledger and line.startswith("| Date"):
            insert_at = i + 2  # after header + separator
            break

    if insert_at is None:
        return {"error": "Could not find Running Ledger table in Bank_Transactions.md"}

    # §6.4 Permission check — expenses only (positive income is always auto-approved)
    if amount < 0:
        recurring = category.lower() in ("subscription", "recurring", "infrastructure")
        perm = permission_check(
            "payment", VAULT_PATH,
            amount=amount, payee=description, recurring=recurring,
        )
        if perm.requires_approval:
            # Create a Pending_Approval file instead of writing directly
            PENDING_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            approval_file = PENDING_DIR / f"APPROVAL_payment_{ts}.md"
            approval_file.write_text(
                f"""---
type: payment_approval
action: banking_add_transaction
date: {date}
description: {description}
amount: {amount}
tx_type: {tx_type}
category: {category}
created: {datetime.now(timezone.utc).isoformat()}
status: pending
permission_reason: {perm.reason}
---

## Payment Approval Required

**Payee / Description:** {description}
**Amount:** ${abs(amount):.2f}
**Date:** {date}
**Category:** {category}

**Reason approval required:** {perm.reason}

## To Approve
Move this file to `/Approved/` — the orchestrator will add the transaction to Bank_Transactions.md.

## To Reject
Move this file to `/Rejected/`.

---
*Auto-generated by banking_mcp_server §6.4 permission boundary*
""",
                encoding="utf-8",
            )
            return {
                "result": "pending_approval",
                "approval_file": approval_file.name,
                "permission_reason": perm.reason,
                "message": f"Payment requires approval. Review {approval_file.name} in /Pending_Approval/.",
            }

    # §7.3 — Banking write: NEVER retry on any failure. A partial/failed write must
    # always require fresh human approval rather than an automatic retry, to prevent
    # duplicate transactions or inconsistent ledger state.
    # Rate limiting — max 3 banking writes per hour
    try:
        get_limiter(VAULT_PATH).check("banking_write")
    except RateLimitExceededError as e:
        return {"error": str(e), "rate_limited": True}

    try:
        lines.insert(insert_at, new_row)
        BANK_FILE.write_text("\n".join(lines), encoding="utf-8")
    except OSError as e:
        # Vault write failed — do NOT retry; return error requiring fresh approval
        return {
            "error": f"Bank ledger write failed: {e}",
            "retry_safe": False,
            "message": "§7.3: Banking writes are never retried automatically. Submit again once the issue is resolved.",
        }

    # Register payee as known after successful write (income or auto-approved expense)
    if amount < 0:
        add_known_payee(description, VAULT_PATH)

    return {
        "result": "success",
        "added": {
            "date": date,
            "description": description,
            "amount": amount,
            "type": tx_type,
            "category": category,
        },
    }


def _get_summary() -> dict:
    """Aggregate MTD income, expenses, and goal progress from Current_Month.md."""
    result = {
        "income": 0.0, "expenses": 0.0, "net": 0.0,
        "mtd_goal": None, "progress_pct": None,
        "source": "Current_Month.md",
    }

    if MONTH_FILE.exists():
        content = MONTH_FILE.read_text(encoding="utf-8")
        for line in content.splitlines():
            for key, field in [
                ("**Income**",   "income_str"),
                ("**Expenses**", "expenses_str"),
                ("**MTD Goal**", "goal_str"),
            ]:
                if key in line:
                    parts = line.split("|")
                    if len(parts) > 2:
                        val = parts[2].strip().replace("$", "").replace(",", "")
                        try:
                            result[field.replace("_str", "")] = float(val)
                        except ValueError:
                            pass

        income   = result.get("income", 0.0)
        expenses = result.get("expenses", 0.0)
        goal     = result.get("mtd_goal", 0.0)
        result["net"] = round(income + expenses, 2) if expenses < 0 else round(income - expenses, 2)
        result["mtd_goal"] = goal
        result["progress_pct"] = round(income / goal * 100, 1) if goal else None

    return result


# ── MCP Server ────────────────────────────────────────────────────────────────

def main():
    """Run the Banking MCP Server using stdio transport."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp import types
    except ImportError:
        sys.stderr.write("ERROR: mcp package not installed. Run: uv sync\n")
        raise SystemExit(1)

    server = Server("banking-mcp")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="banking_get_transactions",
                description=(
                    "Read transactions from Bank_Transactions.md. "
                    "Filter by days back, category (e.g. 'subscription', 'infrastructure'), "
                    "or type ('income', 'expense'). Returns totals and row list."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days":     {"type": "integer", "description": "How many days back (default: 90)"},
                        "category": {"type": "string",  "description": "Filter by category (optional)"},
                        "type":     {"type": "string",  "description": "Filter by type: income or expense (optional)"},
                    },
                },
            ),
            types.Tool(
                name="banking_add_transaction",
                description=(
                    "Append a new transaction to Bank_Transactions.md Running Ledger. "
                    "Use positive amount for income, negative for expenses."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date":        {"type": "string",  "description": "Date in YYYY-MM-DD format"},
                        "description": {"type": "string",  "description": "Transaction description"},
                        "amount":      {"type": "number",  "description": "Amount (positive=income, negative=expense)"},
                        "type":        {"type": "string",  "description": "Transaction type: income or expense"},
                        "category":    {"type": "string",  "description": "Category: client_payment, subscription, infrastructure, etc."},
                    },
                    "required": ["date", "description", "amount", "type", "category"],
                },
            ),
            types.Tool(
                name="banking_get_summary",
                description=(
                    "Get the current month income, expenses, net, and progress toward the monthly goal. "
                    "Reads from Current_Month.md."
                ),
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="banking_get_subscription_report",
                description=(
                    "Run the full subscription audit against the Subscriptions Inventory in "
                    "Bank_Transactions.md. Applies the 3 audit rules from Business_Goals.md "
                    "(idle >30 days, price increase >20%, duplicate tools) and returns flagged "
                    "subscriptions with monthly/annual saving potential."
                ),
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        if name == "banking_get_transactions":
            result = _get_transactions(
                days=arguments.get("days", 90),
                category=arguments.get("category", ""),
                tx_type=arguments.get("type", ""),
            )
        elif name == "banking_add_transaction":
            result = _add_transaction(
                date=arguments["date"],
                description=arguments["description"],
                amount=float(arguments["amount"]),
                tx_type=arguments["type"],
                category=arguments["category"],
            )
        elif name == "banking_get_summary":
            result = _get_summary()
        elif name == "banking_get_subscription_report":
            result = run_subscription_audit(VAULT_PATH)
        else:
            result = {"error": f"Unknown tool: {name}"}

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
