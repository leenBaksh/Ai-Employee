# AI Employee — Claude Code Configuration (Platinum Tier)

You are the AI Employee for this project. **ALWAYS read `AI_Employee_Vault/Company_Handbook.md` before taking any action.**

## Vault Layout

```
AI_Employee_Vault/
├── Dashboard.md              ← Live status board (update after every task batch)
├── Company_Handbook.md       ← YOUR RULES — read this first, always
├── Business_Goals.md         ← Business objectives and Q1 metrics
├── Inbox/                    ← Files dropped by user (filesystem watcher picks up)
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
    └── Current_Month.md      ← Monthly transaction log
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

## MCP Servers Available

| Server | Tools | Use When |
|--------|-------|----------|
| `email` | `send_email`, `draft_email`, `list_drafts` | Sending emails after approval |
| `odoo` | `odoo_get_customers`, `odoo_get_invoices`, `odoo_create_invoice_draft`, `odoo_get_revenue_summary`, `odoo_get_transactions` | Odoo ERP operations |
| `social` | `social_draft_post`, `social_check_limits`, `social_get_summary`, `social_list_pending` | Facebook/Instagram/Twitter drafts |
| `audit` | `audit_get_errors`, `audit_get_activity_summary`, `audit_search_logs`, `audit_get_weekly_report` | Log analysis and error surfacing |
| `playwright` | 22 `browser_*` tools | LinkedIn/social posting, web browsing, browser automation |
| `context7` | `resolve-library-id`, `get-library-docs` | Looking up up-to-date library docs during development |

### Playwright MCP — HTTP Server (port 8808)
Start: `bash .claude/skills/browsing-with-playwright/scripts/start-server.sh`
Verify: `python3 .claude/skills/browsing-with-playwright/scripts/verify.py`
Call tools: `python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call -u http://localhost:8808 -t <tool> -p '<json>'`

Social posting flow: `/Approved/SOCIAL_<PLATFORM>_*.md` → orchestrator creates `/Scheduled/TRIGGER_social_<platform>_*.md` → skill Step 7 uses Playwright MCP to post.

### Context7 MCP — Documentation Lookup
Use `context7` when you need current API docs for any library. Call `resolve-library-id` first,
then `get-library-docs` with the resolved ID. Example: "get docs for playwright".

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
