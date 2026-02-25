# AI Employee — Demo Video Script
**Hackathon: Building Autonomous FTEs in 2026**
**Version:** v0.4.0 Platinum | **Duration:** ~8–10 minutes

---

## PRE-RECORDING CHECKLIST

- [ ] Obsidian vault open on left half of screen
- [ ] Claude Code terminal open on right half
- [ ] Dashboard.md visible in Obsidian
- [ ] Needs_Action/ folder visible in Obsidian sidebar
- [ ] orchestrator.py running in background terminal
- [ ] Playwright MCP server running (port 8808)
- [ ] LinkedIn logged in (browser session cached)
- [ ] Microphone tested

---

## SCENE 1 — THE HOOK (0:00 – 0:45)

**[Screen: show the Human FTE vs Digital FTE table from the hackathon doc]**

> "What if you could hire a full-time employee — one that works 24 hours a day, 7 days a week, never takes sick days, and costs a fraction of a human salary?"

> "That's exactly what we built. This is the AI Employee — a fully autonomous digital FTE powered by Claude Code."

> "In the next 8 minutes, I'll show you how it reads your emails, drafts replies, posts to LinkedIn, creates invoices in your ERP, and even writes you a Monday morning CEO briefing — all without you lifting a finger."

**[Screen: switch to Obsidian vault with Dashboard.md open]**

> "Everything happens here — in an Obsidian vault. It's the AI's brain, memory, and your real-time dashboard."

---

## SCENE 2 — ARCHITECTURE OVERVIEW (0:45 – 1:30)

**[Screen: show ARCHITECTURE.md diagram in Obsidian or a slide]**

> "The system has four layers."

> "**The Brain** — Claude Code. It reasons, plans, and decides."

> "**The Senses** — Python watchers that monitor Gmail, WhatsApp, LinkedIn, and your filesystem 24/7. When something happens, they write a task file into the vault."

> "**The Memory** — This Obsidian vault. Every task, every draft, every decision is a markdown file here."

> "**The Hands** — MCP servers. Claude never sends an email directly. It writes a draft. A human approves it. Only then does the Email MCP server actually send it via SMTP."

> "This is the key safety guarantee: **Human-in-the-Loop for every external action.**"

---

## SCENE 3 — PROCESS INBOX (1:30 – 3:00)

**[Screen: Obsidian showing Needs_Action/ with task files visible]**

> "Let's start with the inbox. Our Gmail watcher has been running in the background. It found several new emails and converted them into task files here in Needs_Action."

**[Screen: Claude Code terminal]**

> "I'll now run the process-inbox skill."

```
/process-inbox
```

**[Screen: watch Claude read Company_Handbook.md first, then process each file]**

> "Notice it reads the Company Handbook first — every time. That's the AI's operating constitution. It defines what it can do autonomously and what requires human approval."

> "For routine emails — newsletters, notifications — it archives them directly to Done."

> "For anything that requires a reply, it drafts a response and creates an approval file in Pending_Approval. It never sends anything on its own."

**[Screen: Obsidian — show a draft appearing in Drafts/ and approval file in Pending_Approval/]**

> "Here's the HITL gate in action. The AI drafted a reply to a client email. It's waiting for me to approve it before a single byte leaves my server."

---

## SCENE 4 — HITL APPROVAL FLOW (3:00 – 3:45)

**[Screen: Obsidian — open the approval file in Pending_Approval/]**

> "Every approval file tells me exactly what will happen and why. The subject, recipient, full email body — nothing hidden."

> "To approve it, I just drag the file to the Approved folder."

**[Screen: drag file from Pending_Approval/ to Approved/]**

> "The orchestrator detects that move within seconds..."

**[Screen: orchestrator terminal — show it picking up the approval]**

> "...and fires the Email MCP server to send it via SMTP. The task is logged and archived to Done."

> "That's the entire email workflow: watcher → task file → draft → approval → send → log."

---

## SCENE 5 — LINKEDIN POST (3:45 – 5:15)

**[Screen: Claude Code terminal]**

> "Now let's post to LinkedIn. I want to share a business update."

```
/post-linkedin
```

**[Screen: Claude drafting a post — show it reading Business_Goals.md for context]**

> "Claude reads our business goals for context, checks today's post count against the handbook limit of 2 per day, then drafts a post."

**[Screen: Obsidian — To_Post/LinkedIn/ folder — post file appears]**

> "The post is saved here. I can edit it if I want. An approval file is created."

**[Screen: drag approval to Approved/]**

> "I approve it. Now watch what happens."

**[Screen: Playwright browser automation — LinkedIn opens, Start a Post clicked, text typed, Post button clicked]**

> "The Playwright MCP server takes over. It opens a real Chrome browser, navigates to LinkedIn, clicks Start a Post, types the content, and hits Post."

**[Screen: LinkedIn feed showing the published post]**

> "Published. No copy-paste, no manual clicking. The post count is updated, the action is logged."

---

## SCENE 6 — RALPH WIGGUM LOOP (5:15 – 6:00)

**[Screen: Claude Code terminal]**

> "What about complex multi-step tasks — things that take dozens of actions to complete? Claude normally stops after each response. We built something to fix that."

> "We call it the **Ralph Wiggum Stop Hook**. It's named after the Simpsons character who just keeps going."

**[Screen: show .claude/settings.json with the Stop hook registered]**

> "Every time Claude would stop, this Python script runs. If there's an active task in Ralph_State, it returns exit code 2 — which tells Claude Code to inject the continuation prompt and keep working."

```
/ralph-loop
```

**[Screen: Claude autonomously processing a batch of tasks, iterating without stopping]**

> "Now Claude processes the full batch without stopping. When every task is done, Ralph deactivates and Claude stops naturally. Built-in circuit breaker prevents infinite loops."

---

## SCENE 7 — MONDAY CEO BRIEFING (6:00 – 7:00)

**[Screen: Obsidian — Briefings/ folder]**

> "Every Monday morning, the scheduler automatically triggers the CEO Briefing."

```
/weekly-briefing
```

**[Screen: Claude reading Logs/, Done/, Accounting/, Business_Goals.md]**

> "It reads a week's worth of logs, completed tasks, and financial data from Odoo..."

**[Screen: Briefings/ folder — new briefing file appears, open it]**

> "...and generates this. Revenue month-to-date versus target. Completed tasks. Bottlenecks. Subscriptions to audit. Next week's priorities."

> "This isn't a template. It's synthesized from real vault data every single week."

---

## SCENE 8 — PLATINUM: DISTRIBUTED ARCHITECTURE (7:00 – 7:45)

**[Screen: ARCHITECTURE.md — show the Cloud + Local diagram]**

> "The Platinum tier adds something powerful: a distributed Cloud + Local architecture."

> "A cloud VM — Oracle, AWS, anywhere — runs a second agent 24/7. This Cloud Agent handles email triage and drafting around the clock, even when your laptop is closed."

> "It uses a **claim-by-move** pattern. Moving a file from Needs_Action to In_Progress/cloud is a single atomic filesystem rename — a built-in mutex. Two agents can never process the same task."

> "The vault syncs between cloud and local via git. Crucially, secrets — your SMTP password, Gmail credentials — never leave your machine. The Cloud Agent is draft-only by design."

**[Screen: Signals/ folder — HEALTH_local-01.json]**

> "Both agents write health signals every 60 seconds. If either goes offline, an alert appears here in the vault within 5 minutes."

---

## SCENE 9 — DASHBOARD & WRAP UP (7:45 – 8:30)

**[Screen: Obsidian — Dashboard.md]**

```
/update-dashboard
```

**[Screen: Dashboard refreshes with live counts]**

> "The dashboard always reflects live state. Zero items in queue. Tasks processed. LinkedIn post published. Cloud agent online."

> "Let me show you what we built across four tiers in this hackathon:"

> "**Bronze** — Vault structure, handbook, filesystem watcher, basic skills."

> "**Silver** — Gmail integration, LinkedIn automation, WhatsApp Business, email MCP, scheduler."

> "**Gold** — Odoo ERP, social media for all platforms, audit system, Ralph Wiggum autonomous loop."

> "**Platinum** — Distributed Cloud + Local agents, git vault sync, health monitoring."

> "20 agent skills. 6 MCP servers. 5 watchers. One orchestrator. All talking through a markdown vault."

**[Screen: GitHub repo]**

> "The full source is on GitHub. Everything is open, documented, and built on Claude Code."

---

## SCENE 10 — CLOSING (8:30 – 9:00)

**[Screen: Human FTE vs Digital FTE table]**

> "A human FTE works 2,000 hours a year. This agent works 8,760."

> "A human task costs $3 to $6. An agent task costs $0.25 to $0.50."

> "That's not an incremental improvement. That's a category shift."

> "This is what an autonomous digital FTE looks like in 2026."

> "Thank you."

---

## RECORDING TIPS

- **Slow down** when showing file moves in Obsidian — let the viewer see it happen
- **Zoom in** on the terminal when Claude is reasoning through a task
- **Pause 1 second** after each scene transition
- **Pre-stage** a few emails in Needs_Action before recording Scene 3
- Keep total runtime under 10 minutes for hackathon judges
- Add **background music** (lo-fi, low volume) under Scenes 2 and 8
- Use **OBS** or **Loom** for screen + voice recording
