---
name: send-email
description: |
  Draft a reply or new email, save it to /Drafts/, and create an approval request.
  The Email MCP Server sends it after the user moves the approval to /Approved/.
  Use when the user asks to "reply to email", "send an email", or "respond to client".
  Handbook §3: no auto-send — always human approval first.
---

# Send Email — AI Employee Skill

Draft an email, save it for review, then send via Email MCP after approval.

## Step 1: Read Email Rules

```bash
cat AI_Employee_Vault/Company_Handbook.md
```

Key rules (§3 + Email Policy):
- Auto-reply: NEVER — human review first
- New contacts: always create approval in /Pending_Approval/
- Add footer: `*This reply was drafted with AI assistance.*`
- Bulk sends: always require approval

## Step 2: Read the Source Task

If replying to an email task:
```bash
cat "AI_Employee_Vault/Needs_Action/<email_task_file>"
```

Check sender against approved contacts (if Rates.md has client list):
```bash
cat AI_Employee_Vault/Accounting/Rates.md
```

## Step 3: Draft the Email

Write a professional reply following Handbook §1:
- Tone: professional, clear, concise
- Language: match sender's language
- Include all relevant details
- Do NOT include sensitive business/financial data
- Add footer: `*This reply was drafted with AI assistance.*`

## Step 4: Use Email MCP to Save Draft

Call the `draft_email` tool via the Email MCP server:

```
Tool: draft_email
Arguments:
  to: <recipient email>
  subject: Re: <original subject>
  body: <full email body>
```

This saves the draft to `/Drafts/DRAFT_<timestamp>_<subject>.md`.

## Step 5: Create Approval Request

Create `/Pending_Approval/EMAIL_<timestamp>.md`:

```markdown
---
type: approval_request
action: send_email
to: <recipient>
subject: <subject>
draft_file: Drafts/DRAFT_<name>.md
created: <ISO timestamp>
expires: <+24 hours>
status: pending
---

## Email Ready to Send

**To:** <recipient>
**Subject:** <subject>

**Preview:**
<first 200 chars of body>

## To Send
Move this file to /Approved/ — orchestrator will trigger Email MCP.

## To Reject
Move this file to /Rejected/
```

## Step 6: Update Source Task

Edit the email task file:
```yaml
status: draft_created
draft_file: Drafts/DRAFT_<name>.md
approval_file: Pending_Approval/EMAIL_<name>.md
```

## Step 7: Report

```
✅ Email drafted: Drafts/DRAFT_<name>.md
📋 Approval request: Pending_Approval/EMAIL_<name>.md
⏳ Awaiting your approval — move to /Approved/ to send
```

## MCP Server Setup

Ensure Email MCP is configured in Claude Code:

```json
{
  "mcpServers": {
    "email": {
      "command": "uv",
      "args": ["run", "--directory", "<project_path>", "email-mcp"]
    }
  }
}
```

Set in `.env`: `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_HOST`, `SMTP_PORT`
