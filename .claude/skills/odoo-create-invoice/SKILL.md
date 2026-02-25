# Skill: Create Odoo Invoice Draft

**Command:** `/odoo-create-invoice`
**Tier:** Gold
**MCP Required:** odoo

## Purpose
Use the Odoo MCP to create an invoice DRAFT in Odoo ERP. Drafts require human review and posting. Handbook §5: never execute payments or > $100 invoices without `/Approved/` file.

## When to Use
- User asks to "create an invoice in Odoo"
- A task in `/Needs_Action/` requests invoice creation
- Following up on a completed service/project

## Steps

### Step 1 — Read Company Handbook
Read `AI_Employee_Vault/Company_Handbook.md` and `AI_Employee_Vault/Accounting/Rates.md`.

### Step 2 — Identify Customer
Use odoo MCP: `odoo_get_customers(search="<customer name>")`
- Confirm the customer ID matches expectations
- If not found: stop, alert user

### Step 3 — Verify Pre-Approval (> $100)
Check `AI_Employee_Vault/Approved/` for a pre-approval file for this invoice.
- If amount > $100 and no approval: create `/Pending_Approval/INVOICE_<customer>_*.md` and stop.

### Step 4 — Create Invoice Draft
Use odoo MCP: `odoo_create_invoice_draft(customer_id=..., lines=[...])`
- Lines must include: description, quantity, price_unit, account_id
- Creates a DRAFT — does not post or send

### Step 5 — Log and Notify
- Log the action to `/Logs/`
- Create a task in `/Needs_Action/` confirming the draft ID and asking user to review in Odoo

### Step 6 — Update Dashboard
Run `/update-dashboard` to refresh counts.

## Handbook Rules
- > $100 invoices require explicit pre-approval file in `/Approved/`
- Only invoice pre-approved clients (see `Accounting/Rates.md`)
- Never post (finalize) invoices automatically — human must do it in Odoo
