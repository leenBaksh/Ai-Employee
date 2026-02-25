---
type: approval_request
action: send_email
to: client@example.com
subject: "Re: Send January Invoice — Invoice INV-2026-01-001"
created: 2026-02-24T05:15:00Z
expires: 2026-02-25T05:15:00Z
related_draft: Drafts/EMAIL_DRAFT_invoice_reply_ABC_Corp.md
related_invoice: Invoices/INVOICE_2026-01_ABC_Corp.md
---

# Approval Request: Send Invoice Email to ABC Corp

## Summary
Email draft ready to send to **client@example.com** with invoice **INV-2026-01-001** for $500.

## What Will Be Sent
See full draft: `Drafts/EMAIL_DRAFT_invoice_reply_ABC_Corp.md`

## To Approve
Move this file to `/Approved/` — the Email MCP will send it.

## To Reject
Move this file to `/Rejected/` — draft will be kept for manual review.

Per Company Handbook §3: Email to clients requires human approval before sending.
