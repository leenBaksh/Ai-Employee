---
type: email
from: client@example.com
subject: Send January Invoice
received: 2026-02-20T09:00:00Z
priority: high
status: sla_breached
sla_deadline: 2026-02-21T09:00:00Z
sla_alert: Needs_Action/ALERT_sla_breach_client_email.md
---

## Email Content

Hi, could you please send me the invoice for January work?
Amount should be $500 for consulting services.
Thanks!

## What Claude Sees:
- Type: Email requesting invoice
- Customer: Regular client
- Amount: $500
- Urgency: High priority

## What Claude Will Do:
1. Extract customer info
2. Create plan
3. Request approval (amount > threshold)
4. Wait for your approval
5. Execute when approved