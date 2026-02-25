---
name: update-dashboard
description: |
  Refresh the AI Employee Dashboard.md with current vault statistics, recent activity,
  and system status. Use this when the user asks to "update the dashboard", "refresh status",
  or "show me what's happening". Also run this after completing any batch of tasks.
---

# Update Dashboard — AI Employee Skill

Regenerate the `AI_Employee_Vault/Dashboard.md` with live vault data.

## Step 1: Gather Vault Statistics

Run these counts:

```bash
# Count pending tasks
ls AI_Employee_Vault/Needs_Action/*.md 2>/dev/null | wc -l

# Count items done
ls AI_Employee_Vault/Done/ 2>/dev/null | wc -l

# Count pending approvals
ls AI_Employee_Vault/Pending_Approval/*.md 2>/dev/null | wc -l

# Count plans in progress
ls AI_Employee_Vault/Plans/*.md 2>/dev/null | wc -l
```

## Step 2: Check Recent Logs

Read today's log file for recent activity:

```bash
cat "AI_Employee_Vault/Logs/$(date -u +%Y-%m-%d).json" 2>/dev/null || echo "No log entries today."
```

## Step 3: Read Business Goals

```bash
cat AI_Employee_Vault/Business_Goals.md
```

## Step 4: Write Updated Dashboard

Overwrite `AI_Employee_Vault/Dashboard.md` with:

```markdown
# AI Employee Dashboard
---
last_updated: <current ISO timestamp>
status: active
---

## System Status
[✅ or ❌ for each component based on what's running]

## Inbox Summary
- Needs Action: <count>
- Pending Approval: <count>
- Active Plans: <count>
- Done (all time): <count>

## Recent Activity
[Last 5 log entries in human-readable format]

## Business Snapshot
[Key metrics from Business_Goals.md]

## Quick Links
- [Company Handbook](Company_Handbook.md)
- [Business Goals](Business_Goals.md)
- [Needs Action folder](Needs_Action/)
- [Logs folder](Logs/)
```

## Completion

Report: `✅ Dashboard updated at <timestamp>`
