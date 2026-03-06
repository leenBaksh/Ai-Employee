---
name: send-slack
description: |
  Draft a Slack message for human approval using the Slack MCP.
  Can also read channels and add reactions without approval.
  Use when the user asks to "send a Slack message", "post in channel",
  "check Slack", or "react to a message".
  Handbook §3: outbound messages always require approval.
---

# Send Slack — AI Employee Skill

Read Slack channels or draft a message for approval.

## Step 1: Read Operating Rules

```bash
cat AI_Employee_Vault/Company_Handbook.md
```

## Step 2: Determine Action Type

| Task | Approval needed? | Tool |
|------|-----------------|------|
| List channels | ❌ No | `slack: list_channels()` |
| Read messages | ❌ No | `slack: read_channel(channel, limit)` |
| Send message | ✅ Yes | `slack: send_message(channel, text)` |
| Add reaction | ❌ No | `slack: add_reaction(channel, ts, emoji)` |

## Step 3a: Read (no approval needed)

List all channels:
```
slack: list_channels()
```

Read recent messages from a channel:
```
slack: read_channel(channel="#general", limit=20)
```

Note: message `ts` field is the timestamp needed for reactions.

## Step 3b: Draft a Message (HITL)

Compose the message based on context. Follow tone rules from Handbook §1:
- Professional and concise
- No financial details in public channels
- Include context so the recipient has everything they need

```
slack: send_message(
  channel="#channel-name",
  text="<message text>"
)
```

This creates `/Pending_Approval/APPROVAL_slack_message_*.md` — does NOT send.

## Step 3c: Add Reaction (no approval needed)

```
slack: add_reaction(
  channel="C012AB3CD",
  timestamp="1234567890.123456",
  emoji="white_check_mark"
)
```

Common emoji: `thumbsup`, `white_check_mark`, `eyes`, `rocket`, `memo`

## Step 4: Log and Report

For message drafts:
```
✅ Slack message drafted for #<channel>
📋 Approval required: Pending_Approval/APPROVAL_slack_message_*.md
⏳ Move to /Approved/ to send. Move to /Rejected/ to discard.
```

For reads:
```
✅ Read <N> messages from #<channel>
📝 Summary: <key points>
```

## Rules

- NEVER send Slack messages without an approval file (Handbook §3)
- NEVER share financial details, credentials, or client PII in Slack
- Reactions and reads are auto-allowed (low-risk)
- For messages to new contacts/channels: flag for additional review
