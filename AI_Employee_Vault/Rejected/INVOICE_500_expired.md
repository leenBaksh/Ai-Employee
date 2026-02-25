---
type: approval_request
action: create_invoice
amount: 500.00
customer: ABC Corp
reason: Amount exceeds $100 auto-approve threshold
created: 2026-02-20T09:20:00Z
expires: 2026-02-21T09:20:00Z
status: pending
---

# Approval Request: Create Invoice

## Details
- **Customer:** ABC Corp
- **Amount:** $500.00
- **Description:** January consulting services
- **Invoice Date:** 2026-01-31
- **Due Date:** 2026-02-28 (30 days)

## Why Approval is Needed
Amount ($500) exceeds auto-approval threshold ($100)

## What Will Happen If Approved
1. Invoice created in Odoo
2. Sent to client@example.com
3. Logged to audit trail
4. Moved to /Done/

## To Approve This Request
Move this file to `/Approved/` folder

## To Reject This Request
Move this file to `/Rejected/` folder

## Timeline
- Created: 2026-02-20 09:20 AM
- Expires: 2026-02-21 09:20 AM (24 hours)