---
type: scheduled_trigger
job: weekly_business_audit
created: 2026-03-02T16:51:06.954753+00:00
status: pending
---

## Scheduled Job: weekly_business_audit

Run the full weekly business audit for 2026-02-23 to 2026-03-02:
1. Read Company_Handbook.md and Business_Goals.md
2. Use audit MCP `audit_get_weekly_report` for activity summary
3. Use audit MCP `audit_get_errors` to surface errors from the week
4. Use odoo MCP `odoo_get_revenue_summary` for financial data
5. Check vault health: /Needs_Action, /Pending_Approval, /Done counts
6. Identify and flag recurring errors (> 3 occurrences)
7. Write audit report to /Logs/AUDIT_2026-03-02.md
8. Update Dashboard.md with audit findings
9. Run `/weekly-business-audit` skill

---
*Created automatically by Scheduler*
