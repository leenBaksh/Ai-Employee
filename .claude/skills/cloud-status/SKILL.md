# Skill: Cloud Status

**Command:** `/cloud-status`
**Tier:** Platinum

## Purpose
Check the health and activity of the Cloud Agent. Read heartbeat signals,
review Cloud Agent's in-progress items, and surface any offline alerts.

## When to Use
- User asks "is the cloud agent running?", "cloud status", "check cloud"
- Before syncing vault to see if Cloud Agent is ready
- When diagnosing distributed system issues

## Steps

### Step 1 — Read health signals
```bash
cat AI_Employee_Vault/Signals/HEALTH_cloud-01.json 2>/dev/null || echo "No signal found"
cat AI_Employee_Vault/Signals/HEALTH_REPORT.json 2>/dev/null || echo "No report found"
```

### Step 2 — Check in-progress items
```bash
ls AI_Employee_Vault/In_Progress/cloud/ 2>/dev/null || echo "(empty)"
```

### Step 3 — Check for agent offline alerts
```bash
ls AI_Employee_Vault/Needs_Action/ALERT_agent_offline_*.md 2>/dev/null || echo "No offline alerts"
```

### Step 4 — Check recent cloud activity in logs
Read today's log file and filter for `cloud_agent` actor entries.

### Step 5 — Report

```
☁️  Cloud Agent Status
━━━━━━━━━━━━━━━━━━━━━━
Agent ID:       cloud-01
Status:         ✅ Online / ❌ Offline / ❓ Unknown
Last seen:      X minutes ago
In-progress:    N items
Drafts created: N approval requests
Vault sync:     Last pushed Xm ago

Local Agent:    ✅ Online (this machine)
```

If offline: surface the alert and suggest restart steps.
