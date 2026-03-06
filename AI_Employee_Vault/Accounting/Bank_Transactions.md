# Bank Transactions Ledger
---
last_updated: 2026-03-06
source: manual + Odoo sync
note: "Add new transactions here. The AI Employee reads this file during weekly audits."
---

## Running Ledger

| Date | Description | Amount | Type | Category | Status |
|------|-------------|--------|------|----------|--------|
| 2026-02-01 | Client: ABC Corp — Invoice #001 | +$2,000.00 | income | client_payment | cleared |
| 2026-02-05 | Notion Pro subscription | -$16.00 | expense | subscription | cleared |
| 2026-02-05 | Slack Pro subscription | -$12.50 | expense | subscription | cleared |
| 2026-02-10 | Client: Buildzone — Invoice #002 | +$1,500.00 | income | client_payment | cleared |
| 2026-02-12 | GitHub Copilot | -$10.00 | expense | subscription | cleared |
| 2026-02-14 | Adobe Creative Cloud | -$54.99 | expense | subscription | cleared |
| 2026-02-15 | ClickUp Business subscription | -$12.00 | expense | subscription | cleared |
| 2026-02-20 | Zoom Pro subscription | -$15.99 | expense | subscription | cleared |
| 2026-02-22 | AWS (EC2 + S3) | -$43.20 | expense | infrastructure | cleared |
| 2026-02-25 | HubSpot Starter CRM | -$45.00 | expense | subscription | cleared |
| 2026-02-28 | Client: RetailCo — Invoice #003 | +$500.00 | income | client_payment | cleared |
| 2026-03-05 | Notion Pro subscription | -$16.00 | expense | subscription | cleared |
| 2026-03-05 | Slack Pro subscription | -$12.50 | expense | subscription | cleared |

---

## Subscriptions Inventory

Track all recurring costs here. The AI Employee flags these during the weekly audit.

| Tool | Monthly Cost | Last Login / Last Use | Used By | Notes |
|------|-------------|----------------------|---------|-------|
| Notion Pro | $16.00 | 2026-03-04 | Owner | Active — daily notes |
| Slack Pro | $12.50 | 2026-03-05 | Owner + clients | Active — client comms |
| GitHub Copilot | $10.00 | 2026-02-12 | Owner | ⚠️ No use since Feb 12 |
| Adobe Creative Cloud | $54.99 | 2026-01-20 | Owner | ⚠️ Last used Jan 20 — 45+ days ago |
| ClickUp Business | $12.00 | 2026-01-15 | Owner | ⚠️ Duplicate of Notion — no login since Jan |
| Zoom Pro | $15.99 | 2026-03-01 | Owner | Active — client calls |
| HubSpot Starter CRM | $45.00 | 2026-02-01 | Owner | ⚠️ Low usage — 1 login in Feb |

**Total monthly subscriptions:** $166.48
**Software budget threshold:** $500/month (alert at $600 — see Business_Goals.md)

---

## Monthly Summaries

| Month | Income | Expenses | Net | Notes |
|-------|--------|----------|-----|-------|
| Feb 2026 | $4,000.00 | $209.68 | $3,790.32 | First full month |
| Mar 2026 | $0.00 | $28.50 | -$28.50 | Month in progress |

---

_Add transactions here manually or via `/odoo-accounting-summary` to pull from Odoo._
_Run `/weekly-briefing` every Sunday to get proactive subscription recommendations._
