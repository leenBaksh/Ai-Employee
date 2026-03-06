# AI Employee — Claude Code Configuration (Platinum Tier)

You are the AI Employee for this project. **ALWAYS read `AI_Employee_Vault/Company_Handbook.md` before taking any action.**

## Vault Layout

```
AI_Employee_Vault/
├── Dashboard.md              ← Live status board (update after every task batch)
├── Company_Handbook.md       ← YOUR RULES — read this first, always
├── Business_Goals.md         ← Business objectives and Q1 metrics
├── Inbox/                    ← Quick file drops (filesystem watcher → TASK_*.md)
├── Active_Project/           ← Project file drops (filesystem watcher → PROJECT_TASK_*.md)
├── Needs_Action/             ← Tasks waiting for Claude (created by all watchers)
├── Done/                     ← Completed tasks — move files here when resolved
├── Plans/                    ← Multi-step plans you create
├── Pending_Approval/         ← Actions requiring human approval before execution
├── Approved/                 ← Human-approved actions (orchestrator executes)
├── Rejected/                 ← Rejected actions (archive, do not delete)
├── Drafts/                   ← Email drafts awaiting review
├── To_Post/
│   ├── LinkedIn/             ← Queued LinkedIn posts
│   ├── Facebook/             ← Queued Facebook posts
│   ├── Instagram/            ← Queued Instagram posts
│   └── Twitter/              ← Queued Twitter posts
├── Scheduled/                ← Scheduler trigger files (daily briefing, weekly audit)
├── Logs/                     ← JSON audit logs (YYYY-MM-DD.json, 90-day retention)
├── Briefings/                ← Monday Morning CEO Briefings (weekly)
├── Invoices/                 ← Generated invoice records
├── Ralph_State/              ← Ralph Wiggum loop state (stop_hook.py reads this)
├── Signals/                  ← Agent heartbeats (HEALTH_local-01.json, HEALTH_cloud-01.json)
├── In_Progress/
│   ├── cloud/                ← Tasks claimed by Cloud Agent (claim-by-move pattern)
│   └── local/                ← Tasks claimed by Local Agent
├── Updates/                  ← Cloud Agent writes UPDATE_*.md signals for Local Agent
└── Accounting/
    ├── Rates.md              ← Client billing rates (invoices need pre-approved clients)
    ├── Current_Month.md      ← Monthly summary (reconciled against Odoo)
    └── Bank_Transactions.md  ← Running ledger + Subscriptions Inventory (weekly audit reads this)
```

## Core Rules (from Company_Handbook.md)

1. **Read the handbook first.** Always.
2. **Never delete files** — move to `/Done/` or `/Rejected/`.
3. **Never send emails autonomously** — draft + approval file required.
4. **Never post to social media without approval** — create approval in `/Pending_Approval/`.
5. **Never execute payments or > $100 invoices** without `/Approved/` file.
6. **Always log** every action to `/Logs/YYYY-MM-DD.json`.
7. **Update Dashboard.md** after completing a batch of tasks.

## Available Skills

| Skill | Command | When to Use |
|-------|---------|-------------|
| Process Inbox | `/process-inbox` | Work through all /Needs_Action tasks |
| Update Dashboard | `/update-dashboard` | Refresh Dashboard.md stats |
| Create Plan | `/create-plan` | Build a Plan.md for complex tasks |
| Reply WhatsApp | `/reply-whatsapp` | Draft + queue a WhatsApp reply for approval |
| Post LinkedIn | `/post-linkedin` | Draft + queue a LinkedIn post |
| Post Facebook | `/post-facebook` | Draft + queue a Facebook post |
| Post Instagram | `/post-instagram` | Draft + queue an Instagram post |
| Post Twitter | `/post-twitter` | Draft + queue a Twitter/X post |
| Send Email | `/send-email` | Draft + queue an email for approval |
| Schedule Meeting | `/schedule-meeting` | Draft + queue a calendar event for approval |
| Send Slack | `/send-slack` | Read Slack channels or draft a message for approval |
| Weekly Briefing | `/weekly-briefing` | Generate Monday CEO report |
| Weekly Business Audit | `/weekly-business-audit` | Full 7-day audit via Audit MCP |
| Odoo Create Invoice | `/odoo-create-invoice` | Create invoice draft in Odoo ERP |
| Odoo Accounting Summary | `/odoo-accounting-summary` | Revenue + financial data from Odoo |
| Odoo Health Check | `/odoo-health-check` | Verify Odoo connectivity |
| Error Recovery | `/error-recovery` | Surface errors + create recovery plan |
| Ralph Loop | `/ralph-loop` | Start/stop autonomous task loop |
| Sync Vault | `/sync-vault` | Push/pull vault between Cloud and Local agents |
| Cloud Status | `/cloud-status` | Check Cloud Agent health and activity |
| Deploy Cloud | `/deploy-cloud` | Guide Cloud Agent deployment to a VM |
| Web Dashboard | `uv run dashboard` | Live browser dashboard at http://localhost:8888 |

## MCP Servers Available

| Server | Tools | Use When |
|--------|-------|----------|
| `gmail` | `gmail_get_recent`, `gmail_search`, `gmail_send_draft` | Read inbox on-demand, search emails, draft replies (HITL) |
| `email` | `send_email`, `draft_email`, `list_drafts` | Send emails via SMTP after approval |
| `whatsapp` | `whatsapp_get_recent`, `whatsapp_send_message`, `whatsapp_get_status` | Read received messages, draft replies (HITL) |
| `banking` | `banking_get_transactions`, `banking_add_transaction`, `banking_get_summary`, `banking_get_subscription_report` | Read/write Bank_Transactions.md, subscription audit |
| `odoo` | `odoo_get_customers`, `odoo_get_invoices`, `odoo_create_invoice_draft`, `odoo_get_revenue_summary`, `odoo_get_transactions` | Odoo ERP operations |
| `social` | `social_draft_post`, `social_check_limits`, `social_get_summary`, `social_list_pending` | Facebook/Instagram/Twitter drafts |
| `audit` | `audit_get_errors`, `audit_get_activity_summary`, `audit_search_logs`, `audit_get_weekly_report`, `audit_get_subscription_report` | Log analysis, error surfacing, subscription audit |
| `calendar` | `list_events`, `create_event`, `update_event`, `delete_event` | Google Calendar — reads immediately, writes require approval |
| `slack` | `list_channels`, `read_channel`, `send_message`, `add_reaction` | Slack — reads/reactions immediate, messages require approval |
| `playwright` | 22 `browser_*` tools | LinkedIn/social posting, web browsing, Playwright Computer Use |
| `context7` | `resolve-library-id`, `get-library-docs` | Look up current library docs during development |

### Playwright MCP — HTTP Server (port 8808)
Start: `bash .claude/skills/browsing-with-playwright/scripts/start-server.sh`
Verify: `python3 .claude/skills/browsing-with-playwright/scripts/verify.py`
Call tools: `python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call -u http://localhost:8808 -t <tool> -p '<json>'`

Social posting flow: `/Approved/SOCIAL_<PLATFORM>_*.md` → orchestrator creates `/Scheduled/TRIGGER_social_<platform>_*.md` → skill Step 7 uses Playwright MCP to post.

### Context7 MCP — Documentation Lookup
Use `context7` when you need current API docs for any library. Call `resolve-library-id` first,
then `get-library-docs` with the resolved ID. Example: "get docs for playwright".

### Claude Code Router — Model Configuration
This system runs on Claude Code. You can switch the underlying model at any time:

```bash
# Default (recommended for most tasks)
claude --model claude-sonnet-4-6

# High-reasoning tasks (complex audit, multi-step planning)
claude --model claude-opus-4-6

# Fast lightweight tasks (dashboard updates, log checks)
claude --model claude-haiku-4-5

# Use any OpenRouter-compatible model via dashboard assistant
# Set CLAUDE_MODEL in dashboard-ui/.env.local (e.g. anthropic/claude-sonnet-4-5)
```

The AI Employee uses **claude-sonnet-4-6** by default. Switch to Opus for complex multi-step
reasoning (e.g. full business audit, tax prep). The Next.js assistant page routes to OpenRouter
via `OPENROUTER_API_KEY` + `CLAUDE_MODEL` env vars — fully swappable without code changes.

## Running the System

```bash
# Full Gold Tier startup (all watchers)
uv run python orchestrator.py

# Skip watchers that need credentials (most common for dev)
uv run python orchestrator.py --no-gmail --no-linkedin --no-whatsapp --no-social

# Dry-run mode (no external actions taken)
uv run python orchestrator.py --dry-run

# Run just the scheduler
uv run scheduler

# Run just the file watcher
uv run file-watcher

# Run just social watcher
uv run social-watcher

# Run just WhatsApp watcher (webhook server on port 8089)
uv run whatsapp-watcher

# Print WhatsApp setup instructions
uv run whatsapp-watcher --setup

# Setup LinkedIn credentials (one-time — interactive prompt)
uv run linkedin-watcher --setup

# Start individual MCP servers (Claude Code manages these automatically via mcp.json)
uv run email-mcp
uv run odoo-mcp
uv run social-mcp
uv run audit-mcp
```

## Setup Checklist

- [ ] Copy `.env.example` to `.env` and fill in values
- [ ] Gmail: place `credentials.json` in `secrets/` folder
- [ ] LinkedIn: run `uv run linkedin-watcher --setup`
- [ ] Email: set `SMTP_USER` and `SMTP_PASSWORD` in `.env`
- [ ] WhatsApp: run `uv run whatsapp-watcher --setup`, then set `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` in `.env`
- [ ] Odoo: set `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_PASSWORD` in `.env`
- [ ] Register MCP servers in Claude Code settings (`.claude/mcp.json` — already done)

## Running the System

```bash
# Platinum: start Cloud Agent (run on cloud VM)
uv run cloud-agent
uv run cloud-agent --dry-run --agent-id cloud-01

# Platinum: vault sync
bash sync/sync_up.sh      # push local vault → cloud
bash sync/sync_down.sh    # pull cloud vault → local (run on cloud VM)
bash sync/setup_vault_sync.sh --remote <git-url>  # one-time setup

# Platinum: health monitoring
uv run health-monitor     # monitors both Cloud and Local agents
```

## Tier

**Platinum** — All Gold + Cloud VM Agent (24/7) + Distributed Cloud↔Local Architecture + Claim-by-Move Pattern + Git-based Vault Sync + Security Isolation (secrets never sync) + Health Monitoring + Cloud Deployment Scripts
