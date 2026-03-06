---
name: schedule-meeting
description: |
  Draft a calendar event for human approval using the Calendar MCP.
  Lists upcoming schedule, proposes an event, and creates an approval file.
  Use when the user asks to "schedule a meeting", "book a call", "add to calendar",
  or when a task requires scheduling follow-up.
  Handbook §3: calendar writes always require approval.
---

# Schedule Meeting — AI Employee Skill

Draft a new calendar event and queue it for approval.

## Step 1: Read Operating Rules

```bash
cat AI_Employee_Vault/Company_Handbook.md
```

## Step 2: Check Current Schedule

Use the Calendar MCP to see what's already booked:

```
calendar: list_events(days_ahead=14)
```

Look for:
- Conflicts with the proposed time
- Back-to-back meetings (allow 15-min buffer)
- Existing recurring slots

## Step 3: Propose the Event

Based on the task context, determine:
- **Summary** — clear, descriptive title
- **Start / End** — ISO 8601 format: `2026-03-10T14:00:00+02:00`
- **Description** — agenda, context, dial-in link if applicable
- **Attendees** — comma-separated emails (if known)

If the time is unspecified, check the schedule and suggest the next available slot.

## Step 4: Draft the Event (HITL)

```
calendar: create_event(
  summary="<title>",
  start="<ISO datetime>",
  end="<ISO datetime>",
  description="<agenda>",
  attendees="<emails>"
)
```

This creates `/Pending_Approval/APPROVAL_calendar_create_*.md` — it does NOT add to calendar yet.

## Step 5: Log and Report

Log the draft creation and report:

```
✅ Meeting drafted: <title>
📅 Time: <start> → <end>
👥 Attendees: <list>
📋 Approval required: Pending_Approval/APPROVAL_calendar_create_*.md
⏳ Move to /Approved/ to confirm. Move to /Rejected/ to cancel.
```

## Rules

- NEVER create calendar events without an approval file
- Always check for conflicts first
- Include a 15-minute buffer between back-to-back meetings
- For external attendees: flag for additional review (new contact rule, Handbook §3)
