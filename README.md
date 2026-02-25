# Personal AI Employee — Silver Tier

> *Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop.*

A **Silver Tier** implementation of the Personal AI Employee hackathon project.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│              PERSONAL AI EMPLOYEE (Silver Tier)             │
├─────────────────────────────────────────────────────────────┤
│  PERCEPTION (Watchers)                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐    │
│  │ File System  │ │    Gmail     │ │    LinkedIn      │    │
│  │  Watcher     │ │   Watcher    │ │ Watcher+Poster   │    │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────────┘    │
│         └────────────────┼────────────────┘                │
│                          ▼                                  │
│              /Needs_Action/*.md                             │
│                          │                                  │
│  REASONING (Claude Code + Skills)                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ /process-inbox  /create-plan  /send-email             │  │
│  │ /post-linkedin  /weekly-briefing  /update-dashboard   │  │
│  └──────────────────────┬────────────────────────────────┘  │
│                         │                                   │
│         ┌───────────────┴──────────────────┐               │
│         ▼                                  ▼               │
│  /Pending_Approval/              /Done/ (auto-resolved)     │
│         │ (you approve)                                     │
│         ▼                                                   │
│  /Approved/                                                 │
│         │                                                   │
│  ACTION (MCP Servers + HITL Loop)                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Email MCP Server   │  LinkedIn Watcher (poster)     │   │
│  │  (send_email, draft)│  (publishes approved posts)    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  SCHEDULING (scheduler.py)                                  │
│  08:00 daily briefing │ Sunday 22:00 weekly audit           │
│  Every 30min SLA monitor + approval expiry check            │
└─────────────────────────────────────────────────────────────┘
```

---

## Silver Tier Deliverables ✅

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| All Bronze requirements | ✅ | See Bronze section below |
| Gmail Watcher | ✅ | `watchers/gmail_watcher.py` |
| LinkedIn Watcher | ✅ | `watchers/linkedin_watcher.py` |
| LinkedIn Auto-Poster | ✅ | Playwright MCP + `/post-linkedin` skill (Step 7) |
| Claude reasoning loop (Plan.md) | ✅ | `/create-plan` skill |
| Email MCP Server | ✅ | `mcp_servers/email_mcp_server.py` |
| HITL approval workflow | ✅ | `/Approved/` → orchestrator → Email MCP |
| Basic scheduling (cron) | ✅ | `scheduler.py` (daily + weekly) |
| All AI as Agent Skills | ✅ | 6 skills total |

---

## Bronze Tier Deliverables ✅

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Obsidian vault + Dashboard.md | ✅ | `AI_Employee_Vault/Dashboard.md` |
| Company_Handbook.md | ✅ | `AI_Employee_Vault/Company_Handbook.md` |
| File System Watcher | ✅ | `watchers/filesystem_watcher.py` |
| Claude reads/writes vault | ✅ | CLAUDE.md + Agent Skills |
| `/Inbox` `/Needs_Action` `/Done` | ✅ | All created |

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.13+ | All scripts |
| UV | Latest | Package manager |
| Claude Code | Latest | AI reasoning engine |
| Obsidian | v1.10.6+ | Dashboard GUI (optional) |
| Google Cloud account | Free | Gmail API OAuth |
| LinkedIn account | Any | LinkedIn Watcher |
| Gmail App Password | — | Email MCP SMTP sending |

---

## Quick Start

### 1. Install dependencies

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Setup Gmail (Silver Tier)

```
1. Go to console.cloud.google.com
2. Create project → Enable Gmail API
3. Create OAuth credentials (Desktop app) → Download as credentials.json
4. Place in secrets/gmail_credentials.json
5. First run will open browser for OAuth authorization
```

### 4. Setup LinkedIn (Silver Tier)

```bash
uv run linkedin-watcher --setup
# Follow browser prompts to log in
```

### 5. Setup Email Sending (Silver Tier)

```
1. Go to myaccount.google.com → Security → App Passwords
2. Generate app password for "Mail"
3. Set SMTP_USER=your@gmail.com and SMTP_PASSWORD=<app_password> in .env
```

### 6. Register MCP Servers with Claude Code

The project uses three MCP servers. The Email MCP is pre-configured in `.claude/mcp.json`.
Register Playwright and Context7 globally:

```bash
# 1) Playwright MCP (browser automation — LinkedIn posting, web browsing)
claude mcp add --transport stdio playwright npx @playwright/mcp@latest

# 2) Context7 MCP (up-to-date library documentation)
claude mcp add --transport stdio context7 npx @upstash/context7-mcp
```

Or they are already in `.claude/mcp.json` for this project:

```json
{
  "mcpServers": {
    "email":      { "command": "uv",   "args": ["run", "--directory", ".", "email-mcp"] },
    "playwright": { "command": "npx",  "args": ["@playwright/mcp@latest"] },
    "context7":   { "command": "npx",  "args": ["@upstash/context7-mcp"] }
  }
}
```

| MCP Server | Purpose |
|------------|---------|
| `email` | Send/draft emails via SMTP after HITL approval |
| `playwright` | Browser automation — posts to LinkedIn, web navigation |
| `context7` | Fetch up-to-date docs for any library |

### 7. Start the system

```bash
# Full Silver Tier (all watchers + scheduler)
uv run python orchestrator.py

# Without Gmail/LinkedIn (no credentials yet)
uv run python orchestrator.py --no-gmail --no-linkedin
```

---

## Vault Structure

```
AI_Employee_Vault/
├── Dashboard.md               ← Live status (auto-updated)
├── Company_Handbook.md        ← AI operating rules
├── Business_Goals.md          ← Q1 objectives and metrics
├── Inbox/                     ← Drop files here (filesystem watcher)
├── Needs_Action/              ← All incoming tasks (all watchers write here)
├── Done/                      ← Completed tasks
├── Plans/                     ← Multi-step plans (create-plan skill)
├── Pending_Approval/          ← Awaiting your approval
├── Approved/                  ← Approved → orchestrator executes
├── Rejected/                  ← Rejected actions
├── Drafts/                    ← Email drafts awaiting review
├── To_Post/LinkedIn/          ← Queued LinkedIn posts
├── Scheduled/                 ← Scheduler trigger files
├── Logs/                      ← JSON audit logs (YYYY-MM-DD.json)
├── Briefings/                 ← Weekly CEO briefings
├── Invoices/                  ← Invoice records
└── Accounting/
    ├── Rates.md               ← Client billing rates
    └── Current_Month.md       ← Monthly transactions
```

---

## Agent Skills

| Skill | Command | Description |
|-------|---------|-------------|
| Process Inbox | `/process-inbox` | Process all /Needs_Action tasks |
| Update Dashboard | `/update-dashboard` | Refresh Dashboard.md |
| Create Plan | `/create-plan` | Reasoning loop → Plan.md |
| Post LinkedIn | `/post-linkedin` | Draft + queue LinkedIn post |
| Send Email | `/send-email` | Draft + queue email for approval |
| Weekly Briefing | `/weekly-briefing` | Generate Monday CEO report |

---

## HITL Approval Workflow

```
Claude drafts action
        │
        ▼
Creates /Pending_Approval/<action>.md
        │
        │  ← You review
        ▼
Move to /Approved/
        │
        ▼
Orchestrator detects file
        │
        ▼
Executes via MCP Server (email) or Watcher (LinkedIn)
        │
        ▼
Logs action → Moves to /Done/
```

---

## Scheduler Jobs

| Job | Schedule | What It Does |
|-----|----------|--------------|
| Daily Briefing | 08:00 daily | Updates Dashboard, checks SLAs, reviews inbox |
| Weekly Audit | Sunday 22:00 | CEO Briefing, revenue review, bottleneck analysis |
| SLA Monitor | Every 30 min | Flags emails > 24hr old |
| Approval Check | Every 30 min | Flags expired approval requests |

---

## Security

- Credentials stored in `secrets/` (gitignored), never in vault
- DRY_RUN=true prevents all external actions during development
- HITL: sensitive actions always require human file approval
- Gmail: OAuth2 with read-only scope
- Email: App Password (not main password), SMTP TLS
- LinkedIn: session stored locally, never synced
- All actions logged to `/Logs/YYYY-MM-DD.json` (90-day retention)

---

## Tier Declaration

**Silver** — All Bronze requirements + Gmail Watcher, LinkedIn Watcher/Poster, Email MCP Server, Scheduler, HITL Approval Loop, 6 Agent Skills.

---

## Troubleshooting

**Gmail credentials error:**
```bash
ls secrets/gmail_credentials.json   # must exist
uv run gmail-watcher                # will open browser for first-time auth
```

**LinkedIn session expired:**
```bash
uv run linkedin-watcher --setup     # re-login
```

**Email MCP not connecting:**
```bash
uv run email-mcp                    # test run
# Check SMTP_USER and SMTP_PASSWORD in .env
```

**Orchestrator not starting watchers:**
```bash
uv run python orchestrator.py --no-gmail --no-linkedin  # skip unset watchers
```

---

*Personal AI Employee Hackathon 0 — Silver Tier submission*
