---
type: invoice_approval
action: send_invoice
client: Global Corp Ltd
client_email: accounts@globalcorp.com
amount_usd: 1800.00
invoice_file: Invoices/INVOICE_GlobalCorp_Feb2026_DRAFT.md
created: 2026-02-27T14:45:00Z
expires: 2026-02-28T14:45:00Z
priority: high
sla_breached: true
---

## Approval Required — Invoice to Global Corp

**Client:** Global Corp Ltd (accounts@globalcorp.com)
**PO Number:** GC-2026-0892
**Amount: $1,800.00** (exceeds $100 threshold — Handbook §2)
**⚠️ SLA STATUS: BREACHED** (25h+ since request)

## Invoice breakdown
| Service | Hours | Rate | Total |
|---------|-------|------|-------|
| AI Workflow Automation Consulting | 10 | $150/hr | $1,500 |
| System Setup & Onboarding | 2 | $150/hr | $300 |
| **Total** | **12** | | **$1,800** |

## Action
- Add your payment details to the invoice file first
- Move this file to `/Approved/` to send the invoice
- Move to `/Rejected/` to cancel

## Why approval needed
Invoice > $100 — Handbook §2 requires human sign-off before sending.
