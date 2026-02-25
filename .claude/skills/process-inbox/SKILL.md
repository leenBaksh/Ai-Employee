---
name: process-inbox
description: |
  Process all pending task files in the AI Employee vault's /Needs_Action folder.
  For each task file, read its contents, determine the required action, create a Plan,
  and move completed items to /Done. Always reads Company_Handbook.md first.
  Use this skill whenever the user asks to "process inbox", "check tasks", or
  "what needs attention".
---

# Process Inbox — AI Employee Skill

Process all pending items in the Obsidian vault and update the dashboard.

## Step 1: Read Operating Rules

Before processing any tasks, ALWAYS read the handbook first:

```bash
cat AI_Employee_Vault/Company_Handbook.md
```

## Step 2: Inventory the Inbox

List all pending task files:

```bash
ls AI_Employee_Vault/Needs_Action/
```

If the folder is empty, report "Inbox is clear. Nothing to process." and stop.

## Step 3: Process Each Task File

For each `.md` file in `/Needs_Action/`:

1. **Read the task file** to understand what it requires.
2. **Check the `type` field** in the frontmatter:
   - `file_drop` → Summarize the referenced file and suggest an action.
   - `email` → Draft a reply (subject to approval rules in handbook).
   - `alert` → Escalate immediately, do not auto-resolve.
3. **Determine autonomy level** from `Company_Handbook.md`:
   - HIGH autonomy → Complete and move to `/Done/`.
   - LOW autonomy → Create an approval request in `/Pending_Approval/`.

## Step 4: Create a Plan (if multi-step)

For tasks requiring multiple steps, create a plan file:

```
AI_Employee_Vault/Plans/PLAN_<task_name>_<date>.md
```

Plan frontmatter:
```yaml
---
created: <ISO timestamp>
source_task: <task filename>
status: in_progress
---
```

## Step 5: Move Completed Tasks

After fully resolving a task, move its file to `/Done/`:

```bash
mv "AI_Employee_Vault/Needs_Action/<filename>" "AI_Employee_Vault/Done/"
```

## Step 6: Update Dashboard

After processing all tasks, update `AI_Employee_Vault/Dashboard.md`:
- Update the "Recent Activity" section with what was done.
- Update counts (Needs Action, Done, Pending Approval).
- Set `last_updated` to current timestamp.

## Completion

Report a summary:
```
✅ Processed X tasks:
  - <task 1>: <outcome>
  - <task 2>: <outcome>
📋 Pending approval: Y items
📁 Done: Z total
```

## Rules

- NEVER delete files, only move them.
- NEVER send emails or make payments without an approval file in `/Approved/`.
- ALWAYS log actions taken.
- If a task is unclear, move it to `/Needs_Action/` with a note asking for clarification.
