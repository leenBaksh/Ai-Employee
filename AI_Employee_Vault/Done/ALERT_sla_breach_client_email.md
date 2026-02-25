---
type: alert
severity: high
created: 2026-02-23T02:50:00Z
status: pending
related_file: Needs_Action/EMAIL_invoice_client.md
handbook_section: "§1 Communication Standards — 24hr SLA"
---

# ⚠️ ALERT: Client Email SLA Breached

## What Happened
A client email requesting a **$500 January invoice** was received on **2026-02-20 at 09:00 UTC**.

Per **Company Handbook §1**: *"Reply to client inquiries within 24 hours."*

The email is now **72+ hours old — SLA breached by 48 hours.**

## Email Details
- **From:** client@example.com
- **Subject:** Send January Invoice
- **Received:** 2026-02-20 09:00 UTC
- **SLA Deadline:** 2026-02-21 09:00 UTC ❌ MISSED
- **Current Age:** 3 days

## Why AI Cannot Reply Autonomously
Per **Company Handbook §1 & §3 (Email Rules)**:
- Auto-reply is disabled — human review required first
- New contact approval workflow applies
- Per new rules section: *"NEVER assume — always ask first"*

## Action Required From You

**Immediate:** Decide on the invoice and respond to the client.

**Option A — Send the invoice (re-approve):**
1. Reject the expired `INVOICE_500.md` in `/Pending_Approval/`
2. Signal AI Employee to prepare a fresh approval request
3. Approve it → AI Employee drafts email reply for your review
4. You send (or approve AI to send)

**Option B — Decline / defer:**
1. Draft a holding reply to client explaining delay
2. Move `EMAIL_invoice_client.md` to `/Done/` once replied

## Risk
Client has been waiting 3 days for their invoice. Further delay may affect client relationship.
Per **Company Handbook §1 SLA**: Response overdue.

## Related Files
- [Original email task](EMAIL_invoice_client.md)
- [Expired invoice approval](ALERT_invoice_approval_expired.md)
- [Invoice plan](../Plans/PLAN_invoice_client.md)
