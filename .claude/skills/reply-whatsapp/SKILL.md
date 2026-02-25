# Reply WhatsApp — AI Employee Skill

Draft and queue a reply to an incoming WhatsApp Business message.
The reply is sent via Meta WhatsApp Business Cloud API after human approval.

## When to Use
- A `WHATSAPP_*.md` task file exists in `/Needs_Action/`
- User asks to "reply to WhatsApp", "respond on WhatsApp", "answer WhatsApp message"
- Handbook §3: replies always require approval before sending

## Step 1: Read the Task File

```bash
cat "AI_Employee_Vault/Needs_Action/WHATSAPP_<timestamp>_<name>.md"
```

Note the `from_number` and `message_id` from the frontmatter.

## Step 2: Draft a Reply

Write a professional reply (Handbook §1: clear, concise, English unless sender used another language).

Create `AI_Employee_Vault/Drafts/WA_DRAFT_<timestamp>.md`:

```markdown
---
type: whatsapp_draft
to_number: <from_number>
original_message_id: <message_id>
created: <ISO timestamp>
---

**Proposed reply:**

<your drafted reply here>

*This reply was drafted with AI assistance.*
```

## Step 3: Create Approval Request

Create `AI_Employee_Vault/Pending_Approval/WA_REPLY_<timestamp>.md`:

```markdown
---
type: approval_request
action: send_whatsapp_reply
to_number: <from_number>
reply_text: <full reply text — single line>
created: <ISO timestamp>
expires: <ISO timestamp + 24 hours>
related_task: Needs_Action/WHATSAPP_<filename>
related_draft: Drafts/WA_DRAFT_<filename>
---

# Approval: WhatsApp Reply

**To:** +<from_number>
**Draft:** See Drafts/WA_DRAFT_<filename>.md

Move to `/Approved/` to send. Move to `/Rejected/` to cancel.
```

## Step 4: Move Original Task to Done

```bash
mv "AI_Employee_Vault/Needs_Action/WHATSAPP_<filename>.md" "AI_Employee_Vault/Done/"
```

## Step 5: Log the Action

Use `log_action("whatsapp_draft_created", to_number, "success", {...})` pattern.

## Step 6: Report to User

Tell the user:
- Draft is ready at `Drafts/WA_DRAFT_<filename>.md`
- Approval needed at `Pending_Approval/WA_REPLY_<filename>.md`
- Once they move the approval to `/Approved/`, the orchestrator sends the reply

## Rules
- NEVER send WhatsApp messages without an `/Approved/` file (Handbook §3)
- Max reply text length: 4096 characters (WhatsApp limit)
- Add AI disclaimer footer: `*This reply was drafted with AI assistance.*`
- Urgent messages (priority: high) → flag in approval request title
