# AI Employee — System Architecture

**Version:** 0.4.0 (Platinum Tier)
**Date:** 2026-02-26

---

## Overview

The AI Employee is a fully autonomous digital FTE (Full-Time Employee) built on Claude Code. It uses a **vault-centric architecture** where all data flows through a structured Obsidian-compatible markdown vault. Claude acts as the brain, Python watchers act as senses, and MCP servers act as hands.

```
┌──────────────────────────────────────────────────────────────────┐
│                        EXTERNAL WORLD                            │
│  Gmail  ·  LinkedIn  ·  Facebook  ·  Instagram  ·  Twitter      │
│  Odoo ERP  ·  SMTP                                               │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                     WATCHERS (Senses)                            │
│  filesystem_watcher.py  ·  gmail_watcher.py                      │
│  linkedin_watcher.py    ·  social_watcher.py                     │
│  scheduler.py (cron jobs)                                        │
└───────────────────────────┬──────────────────────────────────────┘
                            │  writes .md task files
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                  AI EMPLOYEE VAULT (Memory)                      │
│                                                                  │
│  /Inbox/          ← raw drops from user                         │
│  /Needs_Action/   ← tasks for Claude to process                 │
│  /Plans/          ← multi-step plans Claude creates             │
│  /Pending_Approval/ ← HITL gate (human must approve)           │
│  /Approved/       ← human-approved actions                      │
│  /Rejected/       ← rejected actions (archived)                 │
│  /Done/           ← completed tasks (never delete)              │
│  /Drafts/         ← email drafts awaiting review                │
│  /To_Post/        ← social media post queue                     │
│    └── LinkedIn/  Instagram/ Facebook/ Twitter/                 │
│  /Scheduled/      ← trigger files for Claude                    │
│  /Logs/           ← JSON audit trail (90-day retention)         │
│  /Briefings/      ← Monday CEO briefings                        │
│  /Invoices/       ← invoice records                             │
│  /Accounting/     ← rates, monthly ledger                       │
│  /Ralph_State/    ← Ralph Wiggum loop state                     │
└───────────────────────────┬──────────────────────────────────────┘
                            │  reads tasks
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                   CLAUDE CODE (Brain)                            │
│                                                                  │
│  Agent Skills:                                                   │
│    /process-inbox        /update-dashboard                       │
│    /create-plan          /send-email                             │
│    /post-linkedin        /weekly-briefing                        │
│    /post-facebook        /post-instagram                         │
│    /post-twitter         /odoo-create-invoice                    │
│    /odoo-accounting-summary                                      │
│    /weekly-business-audit /error-recovery                        │
│    /ralph-loop           /odoo-health-check                      │
│                                                                  │
│  Ralph Wiggum Stop Hook: .claude/hooks/stop_hook.py              │
└───────────────────────────┬──────────────────────────────────────┘
                            │  calls MCP tools
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                    MCP SERVERS (Hands)                           │
│                                                                  │
│  email-mcp    → send_email, draft_email, list_drafts            │
│  odoo-mcp     → get_customers, get_invoices, create_invoice_draft│
│               → get_revenue_summary, get_transactions            │
│  social-mcp   → draft_post, check_limits, get_summary           │
│               → list_pending                                     │
│  audit-mcp    → get_errors, get_activity_summary                │
│               → search_logs, get_weekly_report                   │
│  playwright   → browser_* tools (LinkedIn, FB, IG, Twitter)     │
│  context7     → resolve-library-id, get-library-docs            │
└──────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Incoming Email

```
Gmail API poll (120s)
    → gmail_watcher.py
    → writes: Needs_Action/EMAIL_<id>.md
    → Claude reads it
    → Claude drafts reply: Drafts/DRAFT_<ts>.md + Pending_Approval/APPROVAL_<ts>.md
    → User approves (moves to /Approved/)
    → Orchestrator detects → Email MCP → SMTP send
    → Done/EMAIL_<id>.md (archived)
```

## Data Flow: Social Media Post

```
User requests post (or /post-facebook skill)
    → social-mcp: draft_post()
    → writes: To_Post/Facebook/POST_<ts>.md + Pending_Approval/SOCIAL_FACEBOOK_<ts>.md
    → User approves (moves to /Approved/)
    → Orchestrator detects → creates: Scheduled/TRIGGER_social_facebook_<ts>.md
    → Claude runs /post-facebook Step 7
    → Playwright MCP → browser automation → posts to Facebook
    → Logs success → Done/
```

## Data Flow: Odoo Invoice

```
User requests invoice
    → Claude checks Rates.md, identifies customer
    → If amount > $100: writes Pending_Approval/INVOICE_<customer>_<ts>.md → STOP
    → User approves (moves to /Approved/)
    → Orchestrator detects → creates Invoices/INVOICE_<ts>.md
    → Claude uses odoo-mcp: create_invoice_draft()
    → Odoo instance has draft — user reviews and posts manually
```

## Data Flow: Ralph Wiggum Loop

```
User creates: Approved/RALPH_<task>_<ts>.md
    → Orchestrator reads → writes Ralph_State/ralph_current.json (active=true)
    → Claude works on task
    → Claude would normally stop...
    → stop_hook.py runs → reads ralph_current.json → iterations < max
    → Hook returns exit 2 + continuation_prompt
    → Claude continues working
    → Repeat until: active=false OR iterations >= max_iterations
```

---

## Tier-by-Tier Feature Rollout

### Bronze Tier (v0.1)
- Vault structure (all directories)
- Company Handbook (rules engine)
- Filesystem Watcher (Inbox, Needs_Action monitoring)
- Skills: /process-inbox, /update-dashboard
- Dashboard.md, Logs/

### Silver Tier (v0.2)
- Gmail Watcher (OAuth2, INBOX/IMPORTANT polling)
- LinkedIn Watcher + Poster (Playwright MCP)
- Email MCP Server (send_email, draft_email, list_drafts)
- Scheduler (daily briefing, weekly audit, SLA monitor, approval expiry)
- Orchestrator (HITL approval loop, process health)
- Skills: /create-plan, /post-linkedin, /send-email, /weekly-briefing

### Gold Tier (v0.3)
- Social Media (Facebook, Instagram, Twitter) via Playwright MCP
- Odoo ERP MCP (5 tools: customers, invoices, revenue, transactions, create)
- Audit MCP (4 tools: errors, activity, search, weekly report)
- Social MCP (4 tools: draft, limits, summary, list)
- Social Watcher (approval queue for FB/IG/Twitter)
- Ralph Wiggum Stop Hook (autonomous loop until task complete)
- Exponential backoff + repeated-failure alerts in BaseWatcher (Handbook §8)
- New scheduler jobs: Odoo health check, weekly business audit, social limits
- Skills: /post-facebook, /post-instagram, /post-twitter, /odoo-*, /weekly-business-audit, /error-recovery, /ralph-loop

### Platinum Tier (v0.4)
- **Cloud Agent** (`cloud_agent.py`) — 24/7 cloud VM agent, draft-only role
- **Distributed Architecture** — Cloud Agent (draft) + Local Agent (execute)
- **Claim-by-Move Pattern** — agents claim tasks by moving files to `/In_Progress/<agent>/`
- **Git-based Vault Sync** — `sync/` scripts keep Cloud↔Local vault in sync
- **Security Isolation** — secrets (.env, credentials) never sync to cloud via vault .gitignore
- **Health Monitoring** (`cloud/health_monitor.py`) — heartbeat signals + offline alerts
- **Cloud Deployment** (`cloud/setup_cloud.sh`) — systemd service + cron for cloud VM
- **Local Agent Heartbeat** — orchestrator writes `/Signals/HEALTH_local-01.json` every 60s
- Skills: /sync-vault, /cloud-status, /deploy-cloud

---

## Platinum Tier: Distributed Architecture

```
┌─────────────────────────────┐    git sync    ┌─────────────────────────────┐
│      LOCAL MACHINE          │◄──────────────►│      CLOUD VM (24/7)        │
│                             │                │                             │
│  orchestrator.py            │                │  cloud_agent.py             │
│  (Local Agent local-01)     │                │  (Cloud Agent cloud-01)     │
│                             │                │                             │
│  OWNS:                      │                │  OWNS:                      │
│  ✅ Final send/post          │                │  ✅ Email triage             │
│  ✅ WhatsApp responses       │                │  ✅ Draft replies            │
│  ✅ Payments & banking       │                │  ✅ Social post drafts       │
│  ✅ Dashboard.md (sole writer)│               │  ✅ Task claiming            │
│  ✅ Human approval review    │                │                             │
│                             │                │  NEVER:                     │
│                             │                │  ❌ Execute sends            │
│                             │                │  ❌ Read .env secrets        │
│                             │                │  ❌ Write Dashboard.md       │
└─────────────────────────────┘                └─────────────────────────────┘
         ▲                                               ▲
         │                                               │
         └──────── AI_Employee_Vault (git synced) ───────┘
                   (secrets excluded via .gitignore)
```

## Claim-by-Move Pattern (Platinum)

Prevents two agents from processing the same task:
1. Agent moves `Needs_Action/EMAIL_xyz.md` → `In_Progress/cloud/EMAIL_xyz.md`
2. Move is atomic at the filesystem level (rename syscall)
3. Other agents skip files already in `In_Progress/`
4. After completion: agent moves to `Done/`
5. On failure: agent moves back to `Needs_Action/`

---

## Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `orchestrator.py` | Master process manager, HITL approval loop, Ralph state, Dashboard, Local heartbeat |
| `cloud_agent.py` | Cloud-side draft agent, claim-by-move, health signal |
| `cloud/health_monitor.py` | Monitor both agents, write offline alerts |
| `cloud/setup_cloud.sh` | Bootstrap cloud VM (systemd + cron) |
| `sync/setup_vault_sync.sh` | Initialize git-based vault sync |
| `sync/sync_up.sh` | Local → Cloud push |
| `sync/sync_down.sh` | Cloud → Local pull (runs on cloud VM via cron) |
| `scheduler.py` | Cron jobs → trigger files for Claude |
| `watchers/base_watcher.py` | Exponential backoff, repeated-failure alerts (Handbook §8) |
| `watchers/filesystem_watcher.py` | Vault file events → Needs_Action |
| `watchers/gmail_watcher.py` | Gmail poll → Needs_Action |
| `watchers/linkedin_watcher.py` | LinkedIn approval queue → Scheduled |
| `watchers/social_watcher.py` | FB/IG/Twitter approval queue → Scheduled |
| `mcp_servers/email_mcp_server.py` | SMTP email tool |
| `mcp_servers/odoo_mcp_server.py` | Odoo JSON-RPC tools |
| `mcp_servers/social_mcp_server.py` | Social draft/limits tools |
| `mcp_servers/audit_mcp_server.py` | Log query/analysis tools |
| `.claude/hooks/stop_hook.py` | Ralph Wiggum loop (Stop Hook) |
| `.claude/skills/*/SKILL.md` | Agent skill definitions |
| `AI_Employee_Vault/` | Persistent state, task queue, audit trail |

---

## Security Boundaries

All external actions require passing through the **HITL Gate**:

```
Claude proposes → /Pending_Approval/ → Human approves → /Approved/ → Execute
```

No automatic:
- Email sending (always draft → approve)
- Social media posting (always draft → approve → Playwright)
- Invoice creation > $100 (always approve first)
- Payment execution (never — out of scope)

The only autonomous actions are:
- Reading data (Gmail, Odoo, logs, vault)
- Writing to vault (task files, drafts, logs)
- Updating Dashboard.md
- Creating plans and alerts
