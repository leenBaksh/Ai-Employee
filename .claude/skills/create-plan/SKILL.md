---
name: create-plan
description: |
  Claude reasoning loop that reads a task from /Needs_Action/, reasons about it step-by-step,
  and creates a structured Plan.md file in /Plans/. This is the Silver Tier reasoning loop.
  Use when the user says "plan this", "think through", "create a plan for", or when processing
  a complex multi-step task that cannot be resolved in one action.
---

# Create Plan — AI Employee Reasoning Loop

Read a task, think it through, and write a structured Plan.md.

## Step 1: Read Operating Rules

```bash
cat AI_Employee_Vault/Company_Handbook.md
```

## Step 2: Read the Task

Identify the task file to plan. If not specified, check `/Needs_Action/` for the highest-priority item:

```bash
ls -la AI_Employee_Vault/Needs_Action/
cat "AI_Employee_Vault/Needs_Action/<task_file>"
```

## Step 3: Reasoning Loop

Think through the task systematically:

1. **Identify task type** — email, file_drop, invoice, alert, linkedin, payment?
2. **Check handbook rules** — which sections apply? What is the autonomy level?
3. **Identify required information** — what do I know? What is missing?
4. **Identify required actions** — what steps need to happen?
5. **Classify each action** — HIGH autonomy (do it) or LOW autonomy (request approval)?
6. **Identify dependencies** — what must happen before what?
7. **Identify risks** — what could go wrong? What are the safeguards?

## Step 4: Write the Plan File

Create `/Plans/PLAN_<task_name>_<YYYY-MM-DD>.md`:

```markdown
---
created: <ISO timestamp>
status: in_progress
source_task: <task filename>
autonomy_level: high|mixed|low
handbook_sections: [list of sections applied]
---

# Plan: <Task Description>

## Objective
<One sentence: what needs to be achieved>

## Context
<Background: who, what, why>

## Reasoning
<Step-by-step analysis of the task>

## Proposed Steps
1. [x] <completed step>
2. [ ] <next step> — [HIGH/LOW autonomy]
3. [ ] <step requiring approval> — [REQUIRES APPROVAL]

## Approval Requests Needed
<List any files to create in /Pending_Approval/>

## Risks / Considerations
<What could go wrong?>

## Recommendation
<What should happen next?>
```

## Step 5: Create Approval Requests (if needed)

For any LOW autonomy actions, create an approval file in `/Pending_Approval/`:

```markdown
---
type: approval_request
action: <action_type>
to: <recipient>
subject: <subject>
amount: <amount if financial>
created: <ISO timestamp>
expires: <ISO timestamp + 24 hours>
status: pending
---

## Details
<Full description of the action>

## To Approve
Move this file to /Approved/

## To Reject
Move this file to /Rejected/
```

## Step 6: Update Task Status

Edit the source task file frontmatter:
```yaml
status: planned
plan_file: Plans/PLAN_<name>.md
```

## Step 7: Log and Update Dashboard

Log the plan creation to `/Logs/YYYY-MM-DD.json` and update `Dashboard.md`.

## Completion

Report:
```
✅ Plan created: Plans/PLAN_<name>.md
📋 Steps: X total (Y auto, Z require approval)
⏳ Approval requests: N files in /Pending_Approval/
```
