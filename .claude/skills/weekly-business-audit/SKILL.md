# Skill: Weekly Business Audit

**Command:** `/weekly-business-audit`
**Tier:** Gold
**MCP Required:** audit, odoo

## Purpose
Generate a comprehensive 7-day business audit report combining log analysis, Odoo financial data, and vault health metrics. Produces a structured report for the CEO/owner.

## When to Use
- Monday morning (scheduled trigger from scheduler)
- User asks for "weekly audit", "business review", "week in review"
- Before preparing a CEO briefing

## Steps

### Step 1 — Read Handbook and Goals
Read `AI_Employee_Vault/Company_Handbook.md` and `AI_Employee_Vault/Business_Goals.md`.

### Step 2 — Get Activity Summary
Use audit MCP: `audit_get_activity_summary(days=7)`
- Total actions, by type, by actor, by result

### Step 3 — Get Errors
Use audit MCP: `audit_get_errors(days=7, limit=20)`
- Surface top errors from the week
- Identify recurring patterns (same error > 3x)

### Step 4 — Get Full Weekly Report
Use audit MCP: `audit_get_weekly_report()`
- Activity counts, error rate, vault health

### Step 5 — Financial Data (Odoo)
Use odoo MCP: `odoo_get_revenue_summary(months=1)`
- This week's revenue vs target

### Step 6 — Vault Health
Count items in:
- `/Needs_Action/` — tasks pending
- `/Pending_Approval/` — awaiting human decision
- `/Done/` — completed this week
- `/Scheduled/` — scheduled triggers pending

### Step 7 — Write Audit Report
Save to `AI_Employee_Vault/Logs/AUDIT_YYYY-MM-DD.md`:

```markdown
# Weekly Business Audit — YYYY-MM-DD

## Summary
- Period: [start] to [end]
- Total actions: N
- Error rate: X%

## Financial
- Revenue this week: $X
- Target: $X
- Outstanding invoices: N

## Top Issues
1. [error description]
2. [error description]

## Vault Health
- Tasks pending: N
- Approvals needed: N
- Completed: N

## Recommendations
- [action items]
```

### Step 8 — Update Dashboard
Run `/update-dashboard` to reflect latest counts.

### Step 9 — Flag Recurring Issues
If an error type appears > 3 times:
- Create `Needs_Action/ALERT_recurring_error_<type>.md`

## Output
- `AI_Employee_Vault/Logs/AUDIT_YYYY-MM-DD.md`
- Updated `Dashboard.md`
- Optional alerts in `Needs_Action/`
