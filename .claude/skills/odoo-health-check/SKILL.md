# Skill: Odoo Health Check

**Command:** `/odoo-health-check`
**Tier:** Gold
**MCP Required:** odoo

## Purpose
Verify that the Odoo ERP connection is working correctly. Tests authentication and basic data access. Creates alerts if the connection is down.

## When to Use
- Scheduled daily at 09:00 (triggered by scheduler)
- User asks "is Odoo connected?", "check Odoo status"
- Before running any Odoo-dependent workflow
- After changing Odoo credentials

## Steps

### Step 1 — Check Environment Variables
Verify these are set in `.env`:
- `ODOO_URL`
- `ODOO_DB`
- `ODOO_USER`
- `ODOO_PASSWORD`

If missing: create `Needs_Action/ALERT_odoo_config_missing.md` and stop.

### Step 2 — Test Connection
Use odoo MCP: `odoo_get_customers(limit=1)`
- Success: connection is live
- Error: proceed to Step 3

### Step 3 — Handle Failure
If connection fails:
1. Log the error to `/Logs/`
2. Create alert file:

```
AI_Employee_Vault/Needs_Action/ALERT_odoo_down_YYYYMMDD.md
```

```markdown
---
type: alert
severity: high
created: [timestamp]
component: odoo_mcp
---

# Odoo Connection Failed

Error: [error message]
URL: [ODOO_URL]

## Steps to Fix
1. Check Odoo URL in `.env`
2. Verify Odoo instance is running
3. Check credentials (ODOO_USER, ODOO_PASSWORD)
4. Test manually: curl [ODOO_URL]/web/database/list
```

### Step 4 — Log Health Check Result
Write to `/Logs/YYYY-MM-DD.json`:
```json
{
  "action_type": "odoo_health_check",
  "result": "success|error",
  "details": { "url": "...", "latency_ms": 123 }
}
```

### Step 5 — Update Dashboard
Update `Dashboard.md` with Odoo status:
- `Odoo: Connected ✓` or `Odoo: DOWN ✗`

## Expected Output
- Log entry in `/Logs/`
- Dashboard updated
- Alert in `/Needs_Action/` if failed (none if healthy)
