# Skill: Error Recovery

**Command:** `/error-recovery`
**Tier:** Gold
**MCP Required:** audit

## Purpose
Surface errors from audit logs, analyze root causes, and create actionable recovery plans. Pairs with the Audit MCP to give Claude visibility into what went wrong and how to fix it.

## When to Use
- User asks to "fix errors", "recover from failures", "what went wrong"
- After a watcher crash or MCP failure
- High error rate detected in weekly audit
- Alert files in `/Needs_Action/` with type "error" or "alert"

## Steps

### Step 1 — Read Handbook
Read `AI_Employee_Vault/Company_Handbook.md`.

### Step 2 — Fetch Recent Errors
Use audit MCP: `audit_get_errors(days=3, limit=30)`
- Group by `action_type` to find patterns
- Note severity (error vs warning)

### Step 3 — Search for Specific Errors
Use audit MCP: `audit_search_logs(keyword="error", days=3)`
- Also try `audit_search_logs(keyword="failed")`
- `audit_search_logs(keyword="exception")`

### Step 4 — Read Alert Files
List all files in `/Needs_Action/` starting with `ALERT_`:
- Read each one to understand the issue
- Note timestamps and severity

### Step 5 — Analyze Root Causes
For each error category:
- What component failed? (watcher, MCP, orchestrator, scheduler)
- Is it a configuration issue, credentials, network, or code bug?
- Is it recurring?

### Step 6 — Create Recovery Plan
Write a structured plan to `/Plans/PLAN_error_recovery_YYYY-MM-DD.md`:

```markdown
# Error Recovery Plan — YYYY-MM-DD

## Errors Found
1. [error]: [count] occurrences
2. [error]: [count] occurrences

## Root Causes
1. [cause analysis]

## Recovery Actions
- [ ] [specific action]
- [ ] [specific action]

## Prevention
- [how to prevent recurrence]
```

### Step 7 — Execute Safe Fixes
For configuration issues (e.g., missing env vars):
- Update `.env.example` instructions
- Create a `Needs_Action/` task for the user

For recoverable state issues:
- Clear stale lock files
- Reset stuck approval files (re-queue them)

For credential issues:
- Create setup instructions in `Needs_Action/`

### Step 8 — Log Recovery Actions
Log all recovery actions to `/Logs/`.

### Step 9 — Update Dashboard
Run `/update-dashboard`.

## Safety Rules
- Never delete files — only move to `/Done/` or `/Rejected/`
- Never modify core config files without user approval
- If unsure: create a recovery plan and ask for approval
