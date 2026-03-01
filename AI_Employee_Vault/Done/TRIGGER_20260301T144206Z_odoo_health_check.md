---
type: scheduled_trigger
job: odoo_health_check
created: 2026-03-01T14:42:06.558870+00:00
status: pending
---

## Scheduled Job: odoo_health_check

Run the Odoo health check:
1. Read Company_Handbook.md
2. Use odoo MCP tool `odoo_get_customers` with limit=1 to verify connectivity
3. If successful: log result to /Logs/ and update Dashboard.md
4. If failed: create /Needs_Action/ALERT_odoo_down.md with error details
5. Run `/odoo-health-check` skill for full check

---
*Created automatically by Scheduler*
