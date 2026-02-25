# Personal AI Employee — Platinum Tier (v0.4.0)

> *Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop.*

A **Platinum Tier** implementation of the Personal AI Employee hackathon — a fully autonomous Digital FTE (Full-Time Equivalent) powered by Claude Code, Obsidian vault, Python watchers, and MCP servers.

**GitHub:** https://github.com/leenBaksh/Ai-Employee
**Demo:** Open `demo_video.html` in any browser for an interactive 11-slide demo

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        EXTERNAL WORLD                            │
│  Gmail · LinkedIn · Facebook · Instagram · Twitter               │
│  Odoo ERP · SMTP · WhatsApp Business                             │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                     WATCHERS (Senses)                            │
│  filesystem_watcher.py · gmail_watcher.py · linkedin_watcher.py  │
│  whatsapp_watcher.py · social_watcher.py · scheduler.py          │
└───────────────────────────┬──────────────────────────────────────┘
                            │ writes .md task files
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                  AI EMPLOYEE VAULT (Memory)                      │
│  /Inbox  /Needs_Action  /Plans  /Pending_Approval  /Approved     │
│  /Rejected  /Done  /Drafts  /To_Post  /Scheduled  /Logs          │
│  /Briefings  /Invoices  /Accounting  /Ralph_State                │
│  /In_Progress/cloud  /In_Progress/local  /Signals  /Updates      │
└───────────────────────────┬──────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌─────────────────────┐       ┌─────────────────────┐
│   LOCAL AGENT       │       │   CLOUD AGENT       │
│   orchestrator.py   │◄─git─►│   cloud_agent.py    │
│                     │ sync  │                     │
│ ✅ Final send/post  │       │ ✅ Email triage 24/7 │
│ ✅ Approvals        │       │ ✅ Draft replies     │
│ ✅ Dashboard.md     │       │ ✅ Claim-by-move     │
│ ✅ Payments/banking │       │ ❌ Never sends       │
│                     │       │ ❌ Never reads .env  │
└─────────────────────┘       └─────────────────────┘
              │
              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    MCP SERVERS (Hands)                           │
│  email-mcp · odoo-mcp · social-mcp · audit-mcp                  │
│  playwright (browser) · context7 (docs)                         │
└──────────────────────────────────────────────────────────────────┘
```

---

## Tier Checklist

### ✅ Bronze — Foundation
| Requirement | Implementation |
|-------------|----------------|
| Obsidian vault + Dashboard.md | `AI_Employee_Vault/Dashboard.md` |
| Company_Handbook.md | `AI_Employee_Vault/Company_Handbook.md` |
| File System Watcher | `watchers/filesystem_watcher.py` |
| Claude reads/writes vault | `CLAUDE.md` + Agent Skills |
| /Inbox /Needs_Action /Done | All folders created |
| All AI as Agent Skills | `/process-inbox`, `/update-dashboard` |

### ✅ Silver — Functional Assistant
| Requirement | Implementation |
|-------------|----------------|
| Gmail Watcher | `watchers/gmail_watcher.py` — Google OAuth2 |
| WhatsApp + LinkedIn Watchers | `watchers/whatsapp_watcher.py`, `watchers/linkedin_watcher.py` |
| Auto-post LinkedIn | `/post-linkedin` skill + Playwright MCP |
| Claude reasoning loop (Plan.md) | `/create-plan` skill |
| Email MCP Server | `mcp_servers/email_mcp_server.py` |
| HITL approval workflow | `/Approved/` → orchestrator → Email MCP |
| Scheduling | `scheduler.py` — daily 08:00, weekly audit, SLA monitor |
| All AI as Agent Skills | 8 skills total |

### ✅ Gold — Autonomous Employee
| Requirement | Implementation |
|-------------|----------------|
| Full cross-domain integration | Personal (Gmail/WhatsApp) + Business (Odoo/Social) |
| Odoo ERP MCP | `mcp_servers/odoo_mcp_server.py` — 5 tools, JSON-RPC |
| Facebook + Instagram + Twitter | `/post-facebook`, `/post-instagram`, `/post-twitter` via Playwright |
| Multiple MCP servers | email, odoo, social, audit, playwright, context7 |
| Weekly CEO Briefing + Audit | `/weekly-briefing`, `/weekly-business-audit` |
| Error recovery | `/error-recovery` skill + exponential backoff in BaseWatcher |
| Audit logging | `mcp_servers/audit_mcp_server.py` — structured JSON logs |
| Ralph Wiggum loop | `.claude/hooks/stop_hook.py` + Stop Hook mechanism |
| Architecture + Lessons docs | `ARCHITECTURE.md`, `LESSONS_LEARNED.md` |
| All AI as Agent Skills | 17 skills total |

### ✅ Platinum — Always-On Cloud + Local
| Requirement | Implementation |
|-------------|----------------|
| Cloud Agent 24/7 | `cloud_agent.py` — draft-only, claim-by-move pattern |
| Work-zone specialization | Cloud=draft, Local=execute (see ARCHITECTURE.md) |
| Delegation via synced vault | `/In_Progress/cloud/`, `/In_Progress/local/` |
| Git-based vault sync | `sync/setup_vault_sync.sh`, `sync/sync_up.sh`, `sync/sync_down.sh` |
| Claim-by-move rule | Atomic file rename = distributed mutex |
| Security: secrets never sync | `.gitignore` excludes .env, secrets/, credentials |
| Health monitoring | `cloud/health_monitor.py` + `/Signals/HEALTH_*.json` |
| Cloud VM deployment | `cloud/setup_cloud.sh` — systemd + cron |
| All AI as Agent Skills | 20 skills total |

---

## Security Disclosure

| Credential | Storage | Synced to Cloud? |
|------------|---------|-----------------|
| Gmail OAuth token | `secrets/gmail_token.json` (gitignored) | ❌ Never |
| Gmail App Password (SMTP) | `.env` (gitignored) | ❌ Never |
| LinkedIn session | `secrets/linkedin_session/` (gitignored) | ❌ Never |
| WhatsApp access token | `.env` (gitignored) | ❌ Never |
| Odoo password | `.env` (gitignored) | ❌ Never |
| Vault markdown files | `AI_Employee_Vault/` | ✅ Via git (safe) |

**HITL Gate:** All external actions (email send, social post, invoice >$100) require a human to move a file from `/Pending_Approval/` to `/Approved/` before execution. No autonomous sends ever.

**DRY_RUN mode:** Set `DRY_RUN=true` in `.env` to prevent all external actions during development.

---

## Quick Start

```bash
# 1. Install dependencies
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync

# 2. Configure
cp .env.example .env
# Edit .env with your credentials

# 3. Run (skip watchers that need credentials)
uv run python orchestrator.py --no-gmail --no-linkedin --no-whatsapp --no-social

# 4. Open vault in Obsidian
# Point Obsidian at AI_Employee_Vault/

# 5. Try a skill in Claude Code
/process-inbox
/update-dashboard
/weekly-briefing
```

---

## MCP Servers

| Server | Tools | Transport |
|--------|-------|-----------|
| `email` | `send_email`, `draft_email`, `list_drafts` | stdio |
| `odoo` | `get_customers`, `get_invoices`, `create_invoice_draft`, `get_revenue_summary`, `get_transactions` | stdio |
| `social` | `draft_post`, `check_limits`, `get_summary`, `list_pending` | stdio |
| `audit` | `get_errors`, `get_activity_summary`, `search_logs`, `get_weekly_report` | stdio |
| `playwright` | 22 `browser_*` tools | HTTP port 8808 |
| `context7` | `resolve-library-id`, `get-library-docs` | stdio |

Start MCP servers: Claude Code manages them automatically via `.claude/mcp.json`.

---

## Agent Skills (20 total)

| Skill | Command |
|-------|---------|
| Process Inbox | `/process-inbox` |
| Update Dashboard | `/update-dashboard` |
| Create Plan | `/create-plan` |
| Send Email | `/send-email` |
| Reply WhatsApp | `/reply-whatsapp` |
| Post LinkedIn | `/post-linkedin` |
| Post Facebook | `/post-facebook` |
| Post Instagram | `/post-instagram` |
| Post Twitter | `/post-twitter` |
| Weekly Briefing | `/weekly-briefing` |
| Weekly Business Audit | `/weekly-business-audit` |
| Odoo Create Invoice | `/odoo-create-invoice` |
| Odoo Accounting Summary | `/odoo-accounting-summary` |
| Odoo Health Check | `/odoo-health-check` |
| Error Recovery | `/error-recovery` |
| Ralph Loop | `/ralph-loop` |
| Sync Vault | `/sync-vault` |
| Cloud Status | `/cloud-status` |
| Deploy Cloud | `/deploy-cloud` |
| Browse with Playwright | `/browsing-with-playwright` |

---

## Vault Structure

```
AI_Employee_Vault/
├── Dashboard.md               ← Live status (sole writer: Local Agent)
├── Company_Handbook.md        ← AI operating rules
├── Business_Goals.md          ← Q1 objectives
├── Needs_Action/              ← Task queue (all watchers write here)
├── In_Progress/cloud/         ← Cloud Agent claimed tasks
├── In_Progress/local/         ← Local Agent claimed tasks
├── Done/                      ← Completed tasks (never deleted)
├── Pending_Approval/          ← Awaiting human approval
├── Approved/                  ← Approved → orchestrator executes
├── Rejected/                  ← Rejected actions (archived)
├── Drafts/                    ← Email drafts
├── To_Post/LinkedIn|Facebook|Instagram|Twitter/
├── Scheduled/                 ← Scheduler trigger files
├── Signals/                   ← Agent health heartbeats
├── Updates/                   ← Cloud→Local state updates
├── Logs/                      ← JSON audit logs (YYYY-MM-DD.json)
├── Briefings/                 ← Monday CEO briefings
├── Invoices/                  ← Invoice records
├── Ralph_State/               ← Ralph Wiggum loop state
└── Accounting/
    ├── Rates.md
    └── Current_Month.md
```

---

## Tier Declaration

**Platinum** — All Bronze + Silver + Gold requirements, plus distributed Cloud+Local architecture, git-based vault sync, claim-by-move task ownership, health monitoring, cloud VM deployment scripts, and 20 Agent Skills.

---

*Personal AI Employee Hackathon 0 — Platinum Tier (v0.4.0) · leenBaksh · 2026-02-26*
