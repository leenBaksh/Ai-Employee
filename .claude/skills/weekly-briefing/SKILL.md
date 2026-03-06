---
name: weekly-briefing
description: |
  Generate the Monday Morning CEO Briefing. Reads Business_Goals.md, Done/ folder,
  Accounting/Bank_Transactions.md, and Logs/ to produce a comprehensive weekly report
  saved to /Briefings/. Creates Pending_Approval files for flagged subscriptions.
  Use when the user asks for "weekly briefing", "CEO report",
  "weekly summary", or when the scheduler triggers a weekly_audit job.
---

# Weekly Briefing — AI Employee Skill

Generate the Monday Morning CEO Briefing from vault data.
This skill reads, reasons, writes a briefing, AND creates approval requests for
proactive suggestions — it does not just summarise.

## Step 1: Read All Context

```bash
cat AI_Employee_Vault/Company_Handbook.md
cat AI_Employee_Vault/Business_Goals.md
cat AI_Employee_Vault/Accounting/Bank_Transactions.md
cat AI_Employee_Vault/Accounting/Current_Month.md
cat AI_Employee_Vault/Accounting/Rates.md
ls AI_Employee_Vault/Done/
ls AI_Employee_Vault/Logs/
```

## Step 2: Calculate Revenue

From `Bank_Transactions.md` (Running Ledger section):
- Filter rows where `Type = income` and `Date` falls in the current week (Mon–Sun)
- Sum the `Amount` column → **This Week Revenue**
- Sum all income MTD → **Month-to-Date Revenue**
- Compare against `Business_Goals.md` monthly goal → **Progress %**

From `Accounting/Current_Month.md`: cross-check totals for reconciliation status.

## Step 3: Analyse Completed Tasks

From `/Done/` folder: list all files modified this week. For each:
- Extract `type`, `source`, and `received`/`completed` fields from YAML frontmatter
- Categorise: email, invoice, linkedin_post, project_drop, alert_resolved, etc.
- Count per category

From `/Logs/*.json` (this week's dates): count action types:
- `email_sent`, `invoice_created`, `post_published`, `approval_granted`, `alert_triggered`

## Step 4: Identify Bottlenecks

Tasks that took > 2 days (calculated as `completed_at - received`):
- Scan Done/ files for large time deltas
- List any remaining in `/Needs_Action/` with `received:` older than 48 hours
- Check `/Pending_Approval/` for approvals waiting > 24 hours

Format as a table: `Task | Received | Completed | Delay`.

## Step 5: Subscription Audit (Proactive Suggestions)

Read the **Subscriptions Inventory** table from `Bank_Transactions.md`.
Apply rules from `Business_Goals.md → Subscription Audit Rules`:

| Rule | Threshold | Action |
|------|-----------|--------|
| No recent login | > 30 days since Last Login | Flag for cancellation |
| Price increase | > 20% vs prior month | Flag for review |
| Duplicate tool | Same category, 2+ tools | Flag lower-usage one |

For **each flagged subscription**, create an approval file:

```
Pending_Approval/APPROVAL_cancel_sub_<ToolName>_<YYYYMMDD>.md
```

Content template:
```markdown
---
type: approval_request
action: cancel_subscription
tool: <ToolName>
monthly_cost: <$X.XX>
annual_saving: <$X.XX>
reason: <"No login since DATE" | "Duplicate of TOOL" | "Cost increased X%">
created: <ISO timestamp>
expires: <ISO timestamp + 72 hours>
status: pending
---

## Proactive Suggestion: Cancel <ToolName> Subscription

**AI Employee noticed:** <specific observation with dates and amounts>

**Monthly saving:** $<X.XX>
**Annual saving:** $<X.XX>

## Evidence
- Last login: <DATE>
- Monthly charge: $<X.XX> (charged on <DATE>)
- Rule triggered: <Subscription Audit Rule from Business_Goals.md>

## To Approve (cancel subscription)
Move this file to /Approved/

## To Reject (keep subscription)
Move this file to /Rejected/
```

Collect all created approval filenames for the briefing's Proactive Suggestions section.

## Step 6: Write the Briefing

Save to `/Briefings/<YYYY-MM-DD>_Monday_Briefing.md`.

Use this exact output format (matches CEO reference template):

```markdown
---
generated: <ISO timestamp>
period: <YYYY-MM-DD> to <YYYY-MM-DD>
revenue_week: <$X>
revenue_mtd: <$X>
revenue_goal: <$X>
tasks_completed: <N>
bottlenecks: <N>
subscriptions_flagged: <N>
status: final
---

# Monday Morning CEO Briefing
## Week of <Mon date> — <Sun date>

## Executive Summary
<2-3 sentences. Mention revenue vs target, key win of the week, one risk or concern.>

---

## Revenue
- **This Week:** $X
- **MTD:** $X (<X>% of $<goal> target)
- **Trend:** On track / Behind / Ahead

---

## Completed Tasks
- [x] <specific completed item — use plain English, not filenames>
- [x] <next completed item>
- [x] <next completed item>

---

## Bottlenecks
| Task | Expected | Actual | Delay |
|------|----------|--------|-------|
| <task description> | <Xd> | <Yd> | +<Zd> |

<If no bottlenecks: "✅ No bottlenecks this week — all tasks completed within SLA.">

---

## Proactive Suggestions

### Cost Optimization
<For each flagged subscription:>
- **<ToolName>**: <reason — e.g. "No team activity in X days">. Cost: $<X>/month.
  - [ACTION] Cancel subscription? Move `APPROVAL_cancel_sub_<Name>_<DATE>.md` to /Approved/

<Total line:>
> 💰 Potential saving: $<monthly>/month ($<annual>/year) if all above are cancelled.

<If no subscriptions flagged:>
✅ All subscriptions within policy — no action needed.

### Upcoming Deadlines
<For each Active Project in Business_Goals.md, calculate days remaining:>
- <Project Name>: <due date> (<N> days)

---

## Next Week Priorities
1. <highest priority>
2. <second priority>
3. <third priority>

---
*Generated by AI Employee v0.4 — Platinum Tier*
*Approval files created: <N> — check /Pending_Approval/ to action.*
```

## Step 7: Update Dashboard

Add briefing link to Dashboard.md Quick Links section.
Update `## 📊 Weekly Snapshot` section with this week's numbers.

## Step 8: Archive Trigger + Log

If triggered by scheduler, move the trigger file from `/Scheduled/` to `/Done/`.

Log to `/Logs/YYYY-MM-DD.json`:
```json
{
  "action_type": "weekly_briefing_generated",
  "actor": "claude",
  "target": "Briefings/<date>_Monday_Briefing.md",
  "result": "success",
  "details": {
    "revenue_week": "$X",
    "tasks_completed": N,
    "bottlenecks": N,
    "subscriptions_flagged": N,
    "approval_files_created": ["APPROVAL_cancel_sub_X.md", ...]
  }
}
```

## Completion

```
✅ CEO Briefing generated: Briefings/<date>_Monday_Briefing.md
💰 Revenue this week: $X (MTD: $X / $<goal> = X%)
✅ Completed tasks: X
⚠️  Bottlenecks: X
💡 Proactive suggestions: X approval files created in /Pending_Approval/
```

## Rules

- NEVER invent transaction data — only use what is in Bank_Transactions.md
- NEVER cancel subscriptions autonomously — always create an approval file
- If Bank_Transactions.md has no data for the week, note "no transactions recorded" rather than guessing
- Subscription audit rules come from Business_Goals.md — do not apply stricter rules than specified
