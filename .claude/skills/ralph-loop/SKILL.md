# Skill: Ralph Wiggum Loop

**Command:** `/ralph-loop`
**Tier:** Gold
**Mechanism:** Claude Code Stop Hook (`.claude/hooks/stop_hook.py`)

## What Is Ralph Wiggum?

The Ralph Wiggum loop is an autonomous continuation mechanism. When activated, it prevents Claude from stopping at the end of a response and injects a continuation prompt, keeping Claude working until the task is truly complete or the iteration limit is reached.

Named after Ralph Wiggum from The Simpsons — he just keeps going.

## How It Works

1. **Stop Hook** (`.claude/hooks/stop_hook.py`) runs every time Claude would normally stop
2. Hook reads `/Ralph_State/ralph_current.json`
3. If task is **active** and iterations < max: hook returns exit code 2 + re-injects continuation prompt
4. Claude receives the prompt and continues working
5. After `max_iterations` (default: 10), hook allows Claude to stop

## State File Schema

Location: `AI_Employee_Vault/Ralph_State/ralph_current.json`

```json
{
  "active": true,
  "task": "Process all inbox items and update dashboard",
  "iterations": 3,
  "max_iterations": 10,
  "continuation_prompt": "Continue processing /Needs_Action items. Next: check for SLA breaches.",
  "started": "2026-02-23T08:00:00Z",
  "source_file": "RALPH_process_inbox_20260223.md"
}
```

## Starting a Ralph Task

### Option A: Via Approved File
1. Create `/Approved/RALPH_<task>_YYYYMMDD.md`:

```markdown
---
type: ralph_task
action: ralph_loop
task: Process all inbox items and run weekly briefing
max_iterations: 8
continuation_prompt: Continue working through /Needs_Action items. After each item, check if more remain.
---

# Ralph Loop: Process Inbox + Weekly Briefing

Authorized autonomous loop for batch inbox processing.
```

2. Orchestrator detects file, creates `/Ralph_State/ralph_current.json`
3. Next time Claude stops → hook re-injects

### Option B: Direct State File
Create the JSON directly in `/Ralph_State/ralph_current.json`.

## Stopping Ralph Early

Set `"active": false` in `ralph_current.json`, OR:
```bash
python .claude/hooks/stop_hook.py  # exits 0 if active=false
```

## Checking Status
Read `AI_Employee_Vault/Ralph_State/ralph_current.json` to see current iteration count.

## Safety Limits
- Default max: 10 iterations (set `RALPH_MAX_ITERATIONS` in `.env`)
- Circuit breaker: if iterations ≥ max, loop stops regardless
- Each iteration is logged

## Best Use Cases
- Batch inbox processing (many items in `/Needs_Action/`)
- Multi-platform posting campaigns
- Full weekly audit (audit + briefing + dashboard update)
- Odoo data sync + reporting

## Anti-Patterns
- Don't use Ralph for single-task work
- Don't set max_iterations > 20
- Don't use Ralph for tasks requiring human approval mid-loop
