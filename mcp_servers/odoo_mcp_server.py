"""
odoo_mcp_server.py — Odoo ERP MCP Server for the AI Employee.

Connects to Odoo via full JSON-RPC API using httpx.

Exposes 5 MCP tools to Claude:
  - odoo_get_customers(limit?, search?)             → res.partner search/read
  - odoo_get_invoices(status?, limit?)              → account.move with status filter
  - odoo_create_invoice_draft(customer_id, lines)  → create account.move record
  - odoo_get_revenue_summary(months?)              → sum invoice amounts by month
  - odoo_get_transactions(limit?)                  → account.payment search

Environment variables (set in .env):
  ODOO_URL       = https://your-company.odoo.com
  ODOO_DB        = your_database
  ODOO_USER      = admin@company.com
  ODOO_PASSWORD  = your_odoo_password

Run as MCP server (stdio transport):
    uv run odoo-mcp

Security: Never executes payments or creates > $100 invoices without
an /Approved/ file present (enforced at orchestrator level).
"""

import os
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

ODOO_URL      = os.getenv("ODOO_URL", "")
ODOO_DB       = os.getenv("ODOO_DB", "")
ODOO_USER     = os.getenv("ODOO_USER", "")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "")
VAULT_PATH    = Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()
LOGS_DIR      = VAULT_PATH / "Logs"


def _log(action_type: str, target: str, result: str, details: dict = None):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action_type": action_type,
        "actor": "odoo_mcp_server",
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


class OdooClient:
    """Lightweight async Odoo JSON-RPC client using httpx."""

    def __init__(self, url: str, db: str, user: str, password: str):
        self.url      = url.rstrip("/")
        self.db       = db
        self.user     = user
        self.password = password
        self.uid: int | None = None
        self._rpc_id  = 0

    def _next_id(self) -> int:
        self._rpc_id += 1
        return self._rpc_id

    async def authenticate(self) -> int:
        """Authenticate and return uid. Raises on failure."""
        import httpx
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": self._next_id(),
            "params": {
                "db": self.db,
                "login": self.user,
                "password": self.password,
            },
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{self.url}/web/session/authenticate", json=payload)
            resp.raise_for_status()
            data = resp.json()
        if data.get("error"):
            raise RuntimeError(f"Odoo auth error: {data['error']}")
        self.uid = data["result"]["uid"]
        if not self.uid:
            raise RuntimeError("Odoo authentication failed — check ODOO_USER and ODOO_PASSWORD")
        return self.uid

    async def call(self, model: str, method: str, args: list, kwargs: dict = None) -> any:
        """Generic Odoo JSON-RPC call."""
        import httpx
        if self.uid is None:
            await self.authenticate()
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": self._next_id(),
            "params": {
                "model": model,
                "method": method,
                "args": args,
                "kwargs": kwargs or {},
            },
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.url}/web/dataset/call_kw",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
        if data.get("error"):
            raise RuntimeError(f"Odoo RPC error: {data['error']}")
        return data["result"]

    async def search_read(self, model: str, domain: list, fields: list, limit: int = 50) -> list:
        return await self.call(model, "search_read", [domain], {"fields": fields, "limit": limit})

    async def create(self, model: str, vals: dict) -> int:
        return await self.call(model, "create", [vals])


def _get_client() -> OdooClient:
    return OdooClient(ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD)


def _check_config() -> dict | None:
    """Return error dict if Odoo env vars are missing."""
    missing = [v for v in ("ODOO_URL", "ODOO_DB", "ODOO_USER", "ODOO_PASSWORD") if not os.getenv(v)]
    if missing:
        return {"error": f"Missing Odoo config: {', '.join(missing)}. Set in .env"}
    return None


# ── Tool Implementations ───────────────────────────────────────────────────────

async def tool_get_customers(limit: int = 20, search: str = "") -> dict:
    if err := _check_config():
        return err
    try:
        client = _get_client()
        domain = [("is_company", "=", True)]
        if search:
            domain.append(("name", "ilike", search))
        customers = await client.search_read(
            "res.partner",
            domain,
            ["id", "name", "email", "phone", "street", "city", "country_id"],
            limit=limit,
        )
        _log("odoo_get_customers", "res.partner", "success", {"count": len(customers), "search": search})
        return {"customers": customers, "count": len(customers)}
    except Exception as e:
        _log("odoo_get_customers", "res.partner", "error", {"error": str(e)})
        return {"error": str(e)}


async def tool_get_invoices(status: str = "", limit: int = 20) -> dict:
    if err := _check_config():
        return err
    try:
        client = _get_client()
        domain = [("move_type", "in", ["out_invoice", "out_refund"])]
        if status:
            domain.append(("state", "=", status))
        invoices = await client.search_read(
            "account.move",
            domain,
            ["id", "name", "partner_id", "invoice_date", "amount_total", "state", "currency_id"],
            limit=limit,
        )
        _log("odoo_get_invoices", "account.move", "success", {"count": len(invoices), "status_filter": status})
        return {"invoices": invoices, "count": len(invoices)}
    except Exception as e:
        _log("odoo_get_invoices", "account.move", "error", {"error": str(e)})
        return {"error": str(e)}


async def tool_create_invoice_draft(customer_id: int, lines: list[dict], currency_code: str = "USD") -> dict:
    if err := _check_config():
        return err
    try:
        client = _get_client()
        # Build invoice lines
        invoice_lines = []
        for line in lines:
            invoice_lines.append((0, 0, {
                "name": line.get("description", "Service"),
                "quantity": line.get("quantity", 1),
                "price_unit": line.get("price_unit", 0),
                "account_id": line.get("account_id"),  # required — must be provided
            }))

        vals = {
            "move_type": "out_invoice",
            "partner_id": customer_id,
            "invoice_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "invoice_line_ids": invoice_lines,
        }
        invoice_id = await client.create("account.move", vals)
        _log("odoo_create_invoice_draft", f"invoice_{invoice_id}", "success", {
            "customer_id": customer_id, "lines": len(lines)
        })
        return {"success": True, "invoice_id": invoice_id, "message": f"Invoice draft created (ID {invoice_id})"}
    except Exception as e:
        _log("odoo_create_invoice_draft", "account.move", "error", {"error": str(e)})
        return {"error": str(e)}


async def tool_get_revenue_summary(months: int = 3) -> dict:
    if err := _check_config():
        return err
    try:
        client = _get_client()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=months * 30)).strftime("%Y-%m-%d")
        invoices = await client.search_read(
            "account.move",
            [("move_type", "=", "out_invoice"), ("state", "=", "posted"), ("invoice_date", ">=", cutoff)],
            ["invoice_date", "amount_total", "currency_id", "partner_id"],
            limit=500,
        )
        # Group by month
        by_month: dict[str, float] = {}
        for inv in invoices:
            month = str(inv.get("invoice_date", ""))[:7]  # YYYY-MM
            by_month[month] = by_month.get(month, 0) + float(inv.get("amount_total", 0))
        total = sum(by_month.values())
        _log("odoo_get_revenue_summary", "account.move", "success", {"months": months, "total": total})
        return {
            "months": months,
            "period_start": cutoff,
            "total_revenue": round(total, 2),
            "by_month": {k: round(v, 2) for k, v in sorted(by_month.items())},
            "invoice_count": len(invoices),
        }
    except Exception as e:
        _log("odoo_get_revenue_summary", "account.move", "error", {"error": str(e)})
        return {"error": str(e)}


async def tool_get_transactions(limit: int = 20) -> dict:
    if err := _check_config():
        return err
    try:
        client = _get_client()
        payments = await client.search_read(
            "account.payment",
            [("state", "!=", "draft")],
            ["id", "name", "partner_id", "date", "amount", "currency_id", "payment_type", "state"],
            limit=limit,
        )
        _log("odoo_get_transactions", "account.payment", "success", {"count": len(payments)})
        return {"transactions": payments, "count": len(payments)}
    except Exception as e:
        _log("odoo_get_transactions", "account.payment", "error", {"error": str(e)})
        return {"error": str(e)}


# ── MCP Server ────────────────────────────────────────────────────────────────
def main():
    """Run the Odoo MCP Server using stdio transport."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp import types
    except ImportError:
        print("ERROR: mcp package not installed. Run: uv sync")
        raise SystemExit(1)

    server = Server("odoo-mcp")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="odoo_get_customers",
                description="Fetch customers (companies) from Odoo CRM. Optionally filter by name search.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit":  {"type": "integer", "description": "Max records (default: 20)"},
                        "search": {"type": "string",  "description": "Filter by customer name (optional)"},
                    },
                },
            ),
            types.Tool(
                name="odoo_get_invoices",
                description="Fetch customer invoices from Odoo. Filter by status: draft, posted, cancel.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string",  "description": "Invoice state filter: draft|posted|cancel (optional)"},
                        "limit":  {"type": "integer", "description": "Max records (default: 20)"},
                    },
                },
            ),
            types.Tool(
                name="odoo_create_invoice_draft",
                description=(
                    "Create a new invoice DRAFT in Odoo. Does NOT post or send — requires human review. "
                    "Lines must include: description, quantity, price_unit, account_id."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "customer_id": {"type": "integer", "description": "Odoo res.partner ID"},
                        "lines": {
                            "type": "array",
                            "description": "Invoice line items",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "description": {"type": "string"},
                                    "quantity":    {"type": "number"},
                                    "price_unit":  {"type": "number"},
                                    "account_id":  {"type": "integer"},
                                },
                                "required": ["description", "quantity", "price_unit"],
                            },
                        },
                    },
                    "required": ["customer_id", "lines"],
                },
            ),
            types.Tool(
                name="odoo_get_revenue_summary",
                description="Summarize posted invoice amounts by month for the last N months.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "months": {"type": "integer", "description": "How many months back (default: 3)"},
                    },
                },
            ),
            types.Tool(
                name="odoo_get_transactions",
                description="Fetch recent payment transactions from Odoo account.payment.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Max records (default: 20)"},
                    },
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        if name == "odoo_get_customers":
            result = await tool_get_customers(
                limit=arguments.get("limit", 20),
                search=arguments.get("search", ""),
            )
        elif name == "odoo_get_invoices":
            result = await tool_get_invoices(
                status=arguments.get("status", ""),
                limit=arguments.get("limit", 20),
            )
        elif name == "odoo_create_invoice_draft":
            result = await tool_create_invoice_draft(
                customer_id=arguments["customer_id"],
                lines=arguments["lines"],
            )
        elif name == "odoo_get_revenue_summary":
            result = await tool_get_revenue_summary(months=arguments.get("months", 3))
        elif name == "odoo_get_transactions":
            result = await tool_get_transactions(limit=arguments.get("limit", 20))
        else:
            result = {"error": f"Unknown tool: {name}"}

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
