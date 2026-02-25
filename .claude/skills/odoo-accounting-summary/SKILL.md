# Skill: Odoo Accounting Summary

**Command:** `/odoo-accounting-summary`
**Tier:** Gold
**MCP Required:** odoo

## Purpose
Pull revenue, customer, and invoice data from Odoo ERP and produce a structured accounting summary. Used for reporting, CEO briefings, and financial planning.

## When to Use
- User asks for "revenue summary", "accounting overview", "Odoo report"
- Weekly business audit requires financial data
- Preparing for client reviews or board meetings

## Steps

### Step 1 — Read Company Handbook
Read `AI_Employee_Vault/Company_Handbook.md` and `AI_Employee_Vault/Business_Goals.md`.

### Step 2 — Fetch Revenue Summary
Use odoo MCP: `odoo_get_revenue_summary(months=3)`
- Note total revenue, monthly breakdown, invoice count

### Step 3 — Fetch Outstanding Invoices
Use odoo MCP: `odoo_get_invoices(status="posted")`
- Identify unpaid invoices (posted but not paid)

### Step 4 — Fetch Customer List
Use odoo MCP: `odoo_get_customers(limit=20)`
- Note active customers for context

### Step 5 — Fetch Recent Transactions
Use odoo MCP: `odoo_get_transactions(limit=10)`
- Note recent payments received

### Step 6 — Compare to Business Goals
Read `AI_Employee_Vault/Business_Goals.md`:
- Compare actual revenue to monthly target
- Note progress toward Q1 goals

### Step 7 — Write Summary
Save a structured markdown report to `AI_Employee_Vault/Accounting/Summary_YYYY-MM.md`:
- Revenue vs target
- Outstanding invoices
- Recent transactions
- Top customers by invoice value
- Recommendations

### Step 8 — Update Dashboard
Update `AI_Employee_Vault/Dashboard.md` with latest financial snapshot.

## Notes
- Read-only operations — never modifies Odoo data (only `odoo_create_invoice_draft` does)
- All data is fetched fresh from Odoo each time
