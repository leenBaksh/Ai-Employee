---
type: scheduled_trigger
job: weekly_audit
created: 2026-03-29T18:10:21.411221+00:00
status: pending
---

## Scheduled Job: weekly_audit

Run the weekly CEO briefing audit for period 2026-03-22 to 2026-03-29:
1. Read Business_Goals.md for targets and subscription audit rules
2. Count completed tasks in /Done/ from this week
3. Read Accounting/Bank_Transactions.md for revenue and subscription inventory
4. Read Accounting/Current_Month.md for MTD reconciliation
5. Check /Logs/ for all actions this week
6. Identify bottlenecks (tasks that took > 2 days)
7. Run subscription audit — create Pending_Approval/APPROVAL_cancel_sub_*.md for each flagged item
8. Write Monday Morning CEO Briefing to /Briefings/2026-03-29_Monday_Briefing.md
9. Update Dashboard.md with weekly summary
10. Run /weekly-briefing skill for full structured output

---
*Created automatically by Scheduler*
