---
name: ralph-loop
description: |
  Start or stop the Ralph Wiggum autonomous continuation loop.
  Keeps Claude working on a multi-step task until a completion condition is met
  or the iteration limit is reached.
  Use when the user asks to "start ralph", "run autonomously", "loop until done",
  or when a batch task needs multiple Claude turns to complete.
---

# Ralph Wiggum Loop — AI Employee Skill

**Command:** `/ralph-loop`
**Tier:** Gold
**Mechanism:** Claude Code Stop Hook (`.claude/hooks/stop_hook.py`)

## What Is Ralph Wiggum?

The Ralph Wiggum loop is an autonomous continuation mechanism. When activated, it prevents Claude from stopping at the end of a response and injects a continuation prompt, keeping Claude working until the task is truly complete or the iteration limit is reached.

Named after Ralph Wiggum from The Simpsons — he just keeps going.

## How It Works

1. **Stop Hook** (`.claude/hooks/stop_hook.py`) runs every time Claude would normally stop
2. Hook reads `/Ralph_State/ralph_current.json`
3. Hook checks **completion conditions** (see below) — if met, allows stop
4. If task is **active** and iterations < max: hook returns exit code 2 + re-injects continuation prompt
5. Claude receives the prompt and continues working
6. After `max_iterations` (default: 10), hook allows Claude to stop

## Completion Strategies

The hook checks these conditions **before** the circuit breaker, in order:

### Strategy 1: Promise Tag (Simple)

Output `<promise>TASK_COMPLETE</promise>` anywhere in your final response.
The hook scans the transcript and allows stop immediately.

**When to use:** Single-file tasks, linear workflows, when you know the task is done.

```
I have finished processing all 6 inbox items and updated the dashboard.

<promise>TASK_COMPLETE</promise>
```

### Strategy 2: File Movement (Advanced)

Set `source_file` in the state. When that file appears in `Done/`, the hook detects it and allows stop.

**When to use:** Tasks that naturally end by moving a file to Done/ (inbox processing, invoice handling).

```json
{
  "source_file": "TASK_process_inbox_20260310.md"
}
```

### Strategy 3: Max Iterations (Safety Net)

If neither completion strategy triggers, the loop stops after `max_iterations`. This is the circuit breaker — not the intended exit path.

## State File Schema

Location: `AI_Employee_Vault/Ralph_State/ralph_current.json`

```json
{
  "active": true,
  "task": "Process all inbox items and update dashboard",
  "iterations": 3,
  "max_iterations": 10,
  "continuation_prompt": "Continue processing /Needs_Action items. Next: check for SLA breaches.",
  "source_file": "RALPH_process_inbox_20260223.md",
  "started": "2026-02-23T08:00:00Z"
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
continuation_prompt: Continue working through /Needs_Action items. After each item, check if more remain. Output <promise>TASK_COMPLETE</promise> when the inbox is empty.
source_file: RALPH_process_inbox_YYYYMMDD.md
---

# Ralph Loop: Process Inbox + Weekly Briefing

Authorized autonomous loop for batch inbox processing.
```

2. Orchestrator detects file, creates `/Ralph_State/ralph_current.json`
3. Next time Claude stops → hook re-injects

### Option B: Direct State File
Create the JSON directly in `/Ralph_State/ralph_current.json`.

## Stopping Ralph Early

Set `"active": false` in `ralph_current.json`, OR output the promise tag:

```
<promise>TASK_COMPLETE</promise>
```

## Checking Status
Read `AI_Employee_Vault/Ralph_State/ralph_current.json` to see current iteration count and completion reason.

Completion reasons written by hook:
- `promise_tag_detected` — clean completion via promise
- `source_file_in_done` — clean completion via file movement
- `max_iterations_reached` — circuit breaker fired (review if task finished)

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
- Don't rely on max_iterations as the completion signal — use a promise or source_file
