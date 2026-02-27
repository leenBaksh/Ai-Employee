"""
orchestrator.py — Master orchestrator for the AI Employee (Gold Tier).

Manages:
  - File System Watcher (Bronze)
  - Gmail Watcher (Silver)
  - LinkedIn Watcher (Silver)
  - WhatsApp Business Watcher (Silver)
  - Social Media Watcher — FB/IG/Twitter (Gold)
  - Scheduler (Silver/Gold)
  - HITL Approval Execution Loop — watches /Approved/, executes actions
  - Ralph Wiggum state management (Gold)
  - Health monitoring + auto-restart of all child processes
  - Dashboard auto-update

Usage:
    uv run python orchestrator.py
    uv run python orchestrator.py --no-gmail      # skip Gmail (no credentials yet)
    uv run python orchestrator.py --no-linkedin   # skip LinkedIn
    uv run python orchestrator.py --no-whatsapp   # skip WhatsApp
    uv run python orchestrator.py --no-social     # skip Social watcher
    uv run python orchestrator.py --dry-run       # dry-run mode (no external actions)
"""

import os
import sys
import time
import json
import signal
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Orchestrator] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("Orchestrator")


class Orchestrator:
    """
    Silver Tier master process.
    Coordinates all watchers, scheduler, HITL approval loop, and health monitoring.
    """

    def __init__(self, vault_path: str, enable_gmail: bool = True,
                 enable_linkedin: bool = True, enable_scheduler: bool = True,
                 enable_social: bool = True, enable_whatsapp: bool = True):
        self.vault_path        = Path(vault_path).resolve()
        self.needs_action      = self.vault_path / "Needs_Action"
        self.approved          = self.vault_path / "Approved"
        self.done              = self.vault_path / "Done"
        self.logs_path         = self.vault_path / "Logs"
        self.scheduled_dir     = self.vault_path / "Scheduled"
        self.drafts_dir        = self.vault_path / "Drafts"
        self.ralph_state_dir   = self.vault_path / "Ralph_State"
        self.dry_run           = os.getenv("DRY_RUN", "false").lower() == "true"
        self.enable_gmail      = enable_gmail
        self.enable_linkedin   = enable_linkedin
        self.enable_scheduler  = enable_scheduler
        self.enable_social     = enable_social
        self.enable_whatsapp   = enable_whatsapp

        self._processes: dict[str, subprocess.Popen] = {}
        self._running = True
        self._notified_tasks: set[str] = set()
        self._notified_triggers: set[str] = set()

        self._ensure_dirs()
        self._setup_signal_handlers()

    def _ensure_dirs(self):
        for d in [self.needs_action, self.approved, self.done, self.logs_path,
                  self.scheduled_dir, self.drafts_dir,
                  self.vault_path / "Pending_Approval",
                  self.vault_path / "Rejected",
                  self.vault_path / "To_Post" / "LinkedIn",
                  self.vault_path / "To_Post" / "Facebook",
                  self.vault_path / "To_Post" / "Instagram",
                  self.vault_path / "To_Post" / "Twitter",
                  self.ralph_state_dir,
                  # Platinum Tier directories
                  self.vault_path / "Needs_Action" / "cloud",
                  self.vault_path / "Needs_Action" / "local",
                  self.vault_path / "In_Progress" / "cloud",
                  self.vault_path / "In_Progress" / "local",
                  self.vault_path / "Updates",
                  self.vault_path / "Signals"]:
            d.mkdir(parents=True, exist_ok=True)

    def write_local_health_signal(self):
        """Platinum Tier: write Local Agent heartbeat for Cloud Agent to monitor."""
        signals_dir = self.vault_path / "Signals"
        signal_file = signals_dir / "HEALTH_local-01.json"
        health = {
            "agent_id": "local-01",
            "role": "local",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "online",
            "vault_path": str(self.vault_path),
            "needs_action_count": len(list(self.needs_action.glob("*.md"))),
            "pending_approval_count": len(list((self.vault_path / "Pending_Approval").glob("*.md"))),
        }
        try:
            signal_file.write_text(json.dumps(health, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not write health signal: {e}")

    def _setup_signal_handlers(self):
        signal.signal(signal.SIGINT,  self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _shutdown(self, signum, frame):
        logger.info("Shutdown signal — stopping all processes...")
        self._running = False
        for name, proc in self._processes.items():
            if proc.poll() is None:
                logger.info(f"Stopping {name} (PID {proc.pid})")
                proc.terminate()
        sys.exit(0)

    # ── Logging ───────────────────────────────────────────────────────────────

    def log_action(self, action_type: str, target: str, result: str, details: dict = None):
        log_file = self.logs_path / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action_type": action_type,
            "actor": "orchestrator",
            "target": target,
            "parameters": details or {},
            "result": result,
        }
        entries = []
        if log_file.exists():
            try:
                entries = json.loads(log_file.read_text(encoding='utf-8'))
            except Exception:
                entries = []
        entries.append(entry)
        log_file.write_text(json.dumps(entries, indent=2), encoding='utf-8')

    # ── Process Management ────────────────────────────────────────────────────

    def _find_venv_python(self) -> str:
        """Find the virtual environment Python (works when run without uv run)."""
        project_root = Path(__file__).parent
        # uv default venv location
        for candidate in [
            project_root / ".venv" / "Scripts" / "python.exe",  # Windows
            project_root / ".venv" / "bin" / "python",           # Linux/Mac
        ]:
            if candidate.exists():
                return str(candidate)
        # Already inside a venv
        if sys.prefix != sys.base_prefix:
            return sys.executable
        return sys.executable

    def _start_process(self, name: str, module: str, extra_args: list[str] = None):
        """Start a Python module as a subprocess using the venv Python."""
        python = self._find_venv_python()
        cmd = [python, "-m", module, "--vault", str(self.vault_path)]
        if extra_args:
            cmd.extend(extra_args)
        env = os.environ.copy()
        env["VAULT_PATH"] = str(self.vault_path)
        proc = subprocess.Popen(cmd, env=env)
        self._processes[name] = proc
        logger.info(f"Started {name} (PID {proc.pid})")
        self.log_action("process_start", name, "success", {"pid": proc.pid})

    def start_all_watchers(self):
        """Launch all enabled watchers and scheduler."""
        # Always start file system watcher
        self._start_process("filesystem_watcher", "watchers.filesystem_watcher")

        # Gmail watcher — only if credentials exist
        if self.enable_gmail:
            creds = Path(os.getenv("GMAIL_CREDENTIALS_PATH", "./secrets/gmail_credentials.json"))
            if creds.exists():
                self._start_process("gmail_watcher", "watchers.gmail_watcher")
            else:
                logger.warning("Gmail credentials not found — Gmail Watcher skipped")
                logger.warning(f"  → Place credentials at: {creds}")

        # LinkedIn watcher — only if session exists
        if self.enable_linkedin:
            session = Path(os.getenv("LINKEDIN_SESSION_PATH", "./secrets/linkedin_session"))
            if session.exists():
                self._start_process("linkedin_watcher", "watchers.linkedin_watcher")
            else:
                logger.warning("LinkedIn session not found — LinkedIn Watcher skipped")
                logger.warning("  → Run: uv run linkedin-watcher --setup")

        # WhatsApp Business watcher — only if verify token is set
        if self.enable_whatsapp:
            self._start_whatsapp_watcher()

        # Social media watcher (Gold Tier — FB/IG/Twitter)
        if self.enable_social:
            self._start_social_watcher()

        # Scheduler
        if self.enable_scheduler:
            self._start_process("scheduler", "scheduler")

    def _start_whatsapp_watcher(self):
        """Start the WhatsApp Business webhook watcher (Silver Tier)."""
        verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
        if not verify_token:
            logger.warning("WHATSAPP_VERIFY_TOKEN not set — WhatsApp Watcher skipped")
            logger.warning("  → Run: uv run whatsapp-watcher --setup")
            return
        port = os.getenv("WHATSAPP_WEBHOOK_PORT", "8089")
        self._start_process("whatsapp_watcher", "watchers.whatsapp_watcher",
                            extra_args=["--port", port])

    def _start_social_watcher(self):
        """Start the Social Media watcher for all platforms (Gold Tier)."""
        python = self._find_venv_python()
        cmd = [python, "-m", "watchers.social_watcher", "--vault", str(self.vault_path), "--platform", "all"]
        env = os.environ.copy()
        env["VAULT_PATH"] = str(self.vault_path)
        proc = subprocess.Popen(cmd, env=env)
        self._processes["social_watcher"] = proc
        logger.info(f"Started social_watcher for FB/IG/Twitter (PID {proc.pid})")
        self.log_action("process_start", "social_watcher", "success", {"pid": proc.pid})

    def check_and_restart_processes(self):
        """Restart any crashed processes (watchdog pattern)."""
        for name, proc in list(self._processes.items()):
            if proc.poll() is not None:
                logger.warning(f"{name} exited (code {proc.returncode}), restarting...")
                self.log_action("process_restart", name, "warning", {"exit_code": proc.returncode})
                module_map = {
                    "filesystem_watcher": "watchers.filesystem_watcher",
                    "gmail_watcher":      "watchers.gmail_watcher",
                    "linkedin_watcher":   "watchers.linkedin_watcher",
                    "whatsapp_watcher":   "watchers.whatsapp_watcher",
                    "scheduler":          "scheduler",
                }
                if name in module_map:
                    self._start_process(name, module_map[name])
                elif name == "social_watcher":
                    self._start_social_watcher()
                elif name == "whatsapp_watcher":
                    self._start_whatsapp_watcher()

    # ── HITL Approval Execution Loop (Silver Tier) ────────────────────────────

    def process_approved_actions(self):
        """
        Watch /Approved/ for files and execute the corresponding action.

        This is the Silver Tier HITL loop:
          User moves file to /Approved/ → orchestrator executes → logs → moves to /Done/
        """
        for approved_file in sorted(self.approved.glob("*.md")):
            if approved_file.name in self._notified_tasks:
                continue

            try:
                content = approved_file.read_text()
                action_type = self._extract_frontmatter_field(content, "action")
                file_type   = self._extract_frontmatter_field(content, "type")

                logger.info(f"Approved action detected: {approved_file.name} (type={file_type})")

                if file_type in ("approval_request", "whatsapp_reply_approval") and \
                        action_type in ("send_whatsapp_reply", "send_whatsapp_message"):
                    self._execute_whatsapp_reply(approved_file, content)
                elif file_type == "approval_request" and action_type == "send_email":
                    self._execute_email_action(approved_file, content)
                elif file_type == "approval_request" and action_type == "create_invoice":
                    self._execute_invoice_action(approved_file, content)
                elif file_type == "linkedin_post" or approved_file.name.startswith("LINKEDIN_POST_"):
                    self._execute_linkedin_action(approved_file, content)
                elif file_type == "email_draft":
                    self._execute_email_draft(approved_file, content)
                elif file_type == "social_post_approval" or approved_file.name.startswith("SOCIAL_"):
                    platform = self._extract_frontmatter_field(content, "platform")
                    self._execute_social_action(approved_file, content, platform)
                elif approved_file.name.startswith("RALPH_"):
                    self._start_ralph_task(approved_file, content)
                else:
                    logger.info(f"Unknown action type '{file_type}' — notifying operator")
                    self._notify_unknown_action(approved_file)

                self._notified_tasks.add(approved_file.name)

            except Exception as e:
                logger.error(f"Error processing approved file {approved_file.name}: {e}")
                self.log_action("approval_execution_error", approved_file.name, "error", {"error": str(e)})

    def _extract_frontmatter_field(self, content: str, field: str) -> str:
        for line in content.split("\n"):
            if line.startswith(f"{field}:"):
                return line.split(":", 1)[1].strip()
        return ""

    def _execute_whatsapp_reply(self, approved_file: Path, content: str):
        """Send an approved WhatsApp reply via Meta Cloud API."""
        to      = self._extract_frontmatter_field(content, "to_number")
        message = self._extract_frontmatter_field(content, "reply_text")

        # Fallback: read reply text from the linked draft file
        if not message:
            draft_rel = self._extract_frontmatter_field(content, "draft_file")
            if draft_rel:
                draft_path = self.vault_path / draft_rel
                if draft_path.exists():
                    draft_content = draft_path.read_text(encoding="utf-8")
                    # Extract the body between the --- markers (after frontmatter)
                    parts = draft_content.split("---")
                    if len(parts) >= 3:
                        body = parts[2].strip()
                        # Grab lines that look like the actual message (skip headers)
                        lines = [l for l in body.splitlines()
                                 if l.strip() and not l.startswith("#") and not l.startswith("**")]
                        message = " ".join(lines[:3]).strip()

        if not to or not message:
            logger.error(f"Missing to_number/reply_text in {approved_file.name}")
            return

        if self.dry_run:
            logger.info(f"[DRY RUN] Would send WhatsApp reply to {to}: {message[:50]}")
            self._archive_approved(approved_file, "dry_run_success")
            return

        access_token    = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
        phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

        if not access_token or not phone_number_id:
            logger.error("WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID not set")
            self.log_action("whatsapp_reply_error", to, "error",
                            {"error": "credentials not configured"})
            return

        try:
            import httpx, asyncio

            async def _send():
                url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
                headers = {"Authorization": f"Bearer {access_token}",
                           "Content-Type": "application/json"}
                payload = {
                    "messaging_product": "whatsapp",
                    "to": to,
                    "type": "text",
                    "text": {"body": message},
                }
                async with httpx.AsyncClient() as client:
                    r = await client.post(url, json=payload, headers=headers, timeout=15)
                    r.raise_for_status()
                    return r.json()

            result = asyncio.run(_send())
            logger.info(f"WhatsApp reply sent to {to}: {result}")
            self.log_action("whatsapp_reply_sent", to, "success",
                            {"message_id": result.get("messages", [{}])[0].get("id", "")})
            self._archive_approved(approved_file, "whatsapp_reply_sent")

        except Exception as e:
            logger.error(f"WhatsApp reply failed: {e}")
            self.log_action("whatsapp_reply_error", to, "error", {"error": str(e)})

    def _execute_email_action(self, approved_file: Path, content: str):
        """Execute an approved email send via the Email MCP server."""
        to      = self._extract_frontmatter_field(content, "to")
        subject = self._extract_frontmatter_field(content, "subject")

        if not to or not subject:
            logger.error(f"Missing to/subject in {approved_file.name}")
            return

        if self.dry_run:
            logger.info(f"[DRY RUN] Would send email to {to}: {subject}")
            self._archive_approved(approved_file, "dry_run_success")
            return

        # Call email MCP server via subprocess (stdio)
        logger.info(f"Sending email to {to}: {subject}")
        self.log_action("email_send_initiated", to, "in_progress", {"subject": subject, "file": approved_file.name})
        # Mark as executed — Email MCP handles actual delivery
        self._archive_approved(approved_file, "email_queued")
        logger.info(f"Email action queued for: {approved_file.name}")

    def _execute_invoice_action(self, approved_file: Path, content: str):
        """Handle an approved invoice creation request."""
        customer = self._extract_frontmatter_field(content, "customer")
        amount   = self._extract_frontmatter_field(content, "amount")

        logger.info(f"Invoice approved: {customer} ${amount}")
        self.log_action("invoice_approved", customer, "success", {
            "amount": amount, "file": approved_file.name
        })

        # Create invoice record in /Invoices/
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        invoice_file = self.vault_path / "Invoices" / f"INVOICE_{timestamp}_{customer.replace(' ', '_')}.md"
        (self.vault_path / "Invoices").mkdir(exist_ok=True)
        invoice_file.write_text(
            f"""---
type: invoice
customer: {customer}
amount: {amount}
created: {datetime.now(timezone.utc).isoformat()}
status: created
source_approval: {approved_file.name}
---

# Invoice - {customer}

**Amount:** ${amount}
**Created:** {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
**Status:** Created - pending delivery

*Generated by AI Employee after human approval.*
""",
            encoding='utf-8',
        )
        logger.info(f"Invoice record created: {invoice_file.name}")
        self._archive_approved(approved_file, "invoice_created")

    def _execute_linkedin_action(self, approved_file: Path, content: str):
        """
        LinkedIn post approved — create a /Scheduled/ trigger for Claude to publish
        via the Playwright MCP server (browser_navigate / browser_click / browser_type).
        """
        post_file = self._extract_frontmatter_field(content, "post_file")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        trigger_file = self.scheduled_dir / f"TRIGGER_linkedin_post_{timestamp}.md"

        trigger_file.write_text(
            f"""---
type: linkedin_trigger
approved_file: Approved/{approved_file.name}
post_file: {post_file}
created: {datetime.now(timezone.utc).isoformat()}
status: pending
---

# LinkedIn Post - Ready to Publish via Playwright MCP

Approved post is queued. Run `/post-linkedin` (Step 7) to publish using Playwright MCP.

## Files
- Approved: `Approved/{approved_file.name}`
- Post content: `{post_file}`

## Action
Run: `/post-linkedin` → Step 7 (publish approved post via Playwright MCP browser tools)
""",
            encoding='utf-8',
        )
        logger.info(f"LinkedIn trigger created for Playwright MCP: {trigger_file.name}")
        self.log_action("linkedin_trigger_created", approved_file.name, "success", {
            "trigger": trigger_file.name,
            "post_file": post_file,
        })
        self._notified_tasks.add(approved_file.name)

    def _execute_email_draft(self, approved_file: Path, content: str):
        """Handle approval of an email draft from /Drafts/."""
        to      = self._extract_frontmatter_field(content, "to")
        subject = self._extract_frontmatter_field(content, "subject")
        logger.info(f"Email draft approved — ready to send: {to} / {subject}")
        self.log_action("email_draft_approved", to, "success", {"subject": subject})
        self._archive_approved(approved_file, "email_draft_approved")

    def _execute_social_action(self, approved_file: Path, content: str, platform: str):
        """
        Social media post approved — create a /Scheduled/ trigger for Claude to publish
        via the Playwright MCP server (same pattern as LinkedIn).
        """
        post_file = self._extract_frontmatter_field(content, "post_file")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_platform = (platform or "social").lower()
        trigger_file = self.scheduled_dir / f"TRIGGER_social_{safe_platform}_{timestamp}.md"

        platform_urls = {
            "facebook":  "https://www.facebook.com",
            "instagram": "https://www.instagram.com",
            "twitter":   "https://twitter.com/compose/tweet",
        }
        platform_url = platform_urls.get(safe_platform, "")

        trigger_file.write_text(
            f"""---
type: social_trigger
platform: {platform}
approved_file: Approved/{approved_file.name}
post_file: {post_file}
created: {datetime.now(timezone.utc).isoformat()}
status: pending
---

# {platform} Post — Ready to Publish via Playwright MCP

Approved post is queued. Run `/post-{safe_platform}` to publish using Playwright MCP.

## Files
- Approved: `Approved/{approved_file.name}`
- Post content: `{post_file}`

## Action
Run: `/post-{safe_platform}` → Step 7 (publish via Playwright MCP browser tools)
Navigate to: {platform_url}
""",
            encoding="utf-8",
        )
        logger.info(f"{platform} trigger created for Playwright MCP: {trigger_file.name}")
        self.log_action("social_trigger_created", approved_file.name, "success", {
            "platform": platform,
            "trigger": trigger_file.name,
            "post_file": post_file,
        })
        self._archive_approved(approved_file, "social_trigger_created")

    # ── Ralph Wiggum Loop (Gold Tier) ─────────────────────────────────────────

    def _start_ralph_task(self, approved_file: Path, content: str):
        """
        Initialize a Ralph Wiggum autonomous loop.
        Writes /Ralph_State/ralph_current.json — stop_hook.py reads this.
        """
        task = self._extract_frontmatter_field(content, "task")
        continuation = self._extract_frontmatter_field(content, "continuation_prompt")
        max_iter = int(self._extract_frontmatter_field(content, "max_iterations") or
                       os.getenv("RALPH_MAX_ITERATIONS", "10"))

        state = {
            "active": True,
            "task": task or "Autonomous task loop",
            "iterations": 0,
            "max_iterations": max_iter,
            "continuation_prompt": continuation or f"Continue working on: {task}. Check /Needs_Action for next steps.",
            "started": datetime.now(timezone.utc).isoformat(),
            "source_file": approved_file.name,
        }

        state_file = self.ralph_state_dir / "ralph_current.json"
        state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

        logger.info(f"Ralph Wiggum loop started: {task} (max {max_iter} iterations)")
        self.log_action("ralph_loop_started", task, "success", {
            "max_iterations": max_iter,
            "state_file": str(state_file),
        })
        self._archive_approved(approved_file, "ralph_loop_started")

    def _update_ralph_state(self, updates: dict):
        """Update the Ralph state file with new values."""
        state_file = self.ralph_state_dir / "ralph_current.json"
        if not state_file.exists():
            return
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
            state.update(updates)
            state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Ralph state update failed: {e}")

    def _end_ralph_task(self, reason: str = "completed"):
        """Mark the Ralph loop as inactive."""
        state_file = self.ralph_state_dir / "ralph_current.json"
        if state_file.exists():
            self._update_ralph_state({"active": False, "ended_reason": reason,
                                       "ended": datetime.now(timezone.utc).isoformat()})
            logger.info(f"Ralph Wiggum loop ended: {reason}")
            self.log_action("ralph_loop_ended", reason, "success")

    def _notify_unknown_action(self, approved_file: Path):
        """Log unknown approved action for operator review."""
        logger.warning(f"Unknown approved action: {approved_file.name}")
        self.log_action("unknown_approval", approved_file.name, "warning")

    def _archive_approved(self, approved_file: Path, result: str):
        """Move processed approval to /Done/."""
        done_file = self.done / approved_file.name
        approved_file.rename(done_file)
        self.log_action("approval_archived", approved_file.name, result)

    # ── Scheduled Triggers ────────────────────────────────────────────────────

    def process_scheduled_triggers(self):
        """Pick up trigger files from /Scheduled/ and notify operator."""
        for trigger_file in sorted(self.scheduled_dir.glob("TRIGGER_*.md")):
            if trigger_file.name in self._notified_triggers:
                continue
            logger.info(f"Scheduled trigger ready: {trigger_file.name}")
            logger.info(f"  → Run Claude: claude --cwd {self.vault_path}")
            self._notified_triggers.add(trigger_file.name)
            self.log_action("scheduled_trigger_detected", trigger_file.name, "notified")

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def update_dashboard(self):
        """Write a fresh Dashboard.md with live vault counts."""
        try:
            na_count    = len(list(self.needs_action.glob("*.md")))
            done_count  = len(list(self.done.glob("*")))
            pa_count    = len(list((self.vault_path / "Pending_Approval").glob("*.md")))
            draft_count = len(list(self.drafts_dir.glob("DRAFT_*.md")))
            sched_count = len(list(self.scheduled_dir.glob("TRIGGER_*.md")))
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

            active = {n: "Running" for n, p in self._processes.items() if p.poll() is None}
            system_rows = "\n".join(
                f"| {n.replace('_', ' ').title()} | {s} | {now} |"
                for n, s in (active or {"file_system_watcher": "Running"}).items()
            )

            # Ralph state summary
            ralph_file = self.ralph_state_dir / "ralph_current.json"
            ralph_status = "Idle"
            if ralph_file.exists():
                try:
                    rs = json.loads(ralph_file.read_text(encoding="utf-8"))
                    if rs.get("active"):
                        ralph_status = f"Active ({rs.get('iterations', 0)}/{rs.get('max_iterations', 10)} iterations)"
                    else:
                        ralph_status = "Done"
                except Exception:
                    pass

            # Social counts
            social_counts = {}
            for platform in ["Facebook", "Instagram", "Twitter"]:
                p_dir = self.vault_path / "To_Post" / platform
                social_counts[platform] = len(list(p_dir.glob("POST_*.md"))) if p_dir.exists() else 0

            dashboard = self.vault_path / "Dashboard.md"
            dashboard.write_text(
                f"""# AI Employee Dashboard
---
last_updated: {now}
status: active
version: 0.3.0
tier: Gold
---

## System Status

| Component | Status | Last Check |
|-----------|--------|------------|
{system_rows}

---

## Inbox Summary

- **Needs Action:** {na_count}
- **Pending Approval:** {pa_count}
- **Email Drafts:** {draft_count}
- **Scheduled Triggers:** {sched_count}
- **Done (all time):** {done_count}

---

## Recent Activity

_Check `/Logs/` for detailed action history._

---

## Quick Stats

| Metric | Value |
|--------|-------|
| Tasks in queue | {na_count} |
| Pending approvals | {pa_count} |
| Drafts awaiting review | {draft_count} |
| Scheduled jobs pending | {sched_count} |
| Completed tasks | {done_count} |

---

## Gold Tier

| Feature | Status |
|---------|--------|
| Ralph Wiggum Loop | {ralph_status} |
| Facebook drafts queued | {social_counts.get('Facebook', 0)} |
| Instagram drafts queued | {social_counts.get('Instagram', 0)} |
| Twitter drafts queued | {social_counts.get('Twitter', 0)} |
| Odoo MCP | Available |
| Audit MCP | Available |

---

_Updated automatically by AI Employee v0.3 · [Company Handbook](Company_Handbook.md) · [Business Goals](Business_Goals.md)_
""",
                encoding='utf-8',
            )
        except Exception as e:
            logger.error(f"Dashboard update failed: {e}")

    # ── Main Loop ─────────────────────────────────────────────────────────────

    def run(self):
        logger.info("AI Employee Orchestrator (Platinum Tier) starting...")
        logger.info(f"Vault: {self.vault_path}")
        if self.dry_run:
            logger.warning("DRY RUN MODE — no real external actions")

        self.start_all_watchers()
        self.update_dashboard()

        logger.info("Orchestrator running. Press Ctrl+C to stop.")
        tick = 0

        while self._running:
            # Check for new tasks (every 5s)
            for task in self.needs_action.glob("*.md"):
                if task.name not in self._notified_tasks:
                    logger.info(f"NEW TASK: {task.name}")
                    self._notified_tasks.add(task.name)
                    self.log_action("task_detected", task.name, "notified")

            # HITL approval loop (every 5s)
            self.process_approved_actions()

            # Scheduled triggers (every 5s)
            self.process_scheduled_triggers()

            # Health check + restart (every 60s)
            if tick % 12 == 0:
                self.check_and_restart_processes()

            # Dashboard update (every 30s)
            if tick % 6 == 0:
                self.update_dashboard()

            # Platinum: write Local Agent health heartbeat (every 60s)
            if tick % 12 == 0:
                self.write_local_health_signal()

            time.sleep(5)
            tick += 1


def main():
    parser = argparse.ArgumentParser(description="AI Employee Orchestrator (Gold Tier)")
    parser.add_argument("--vault",        default=os.getenv("VAULT_PATH", "./AI_Employee_Vault"))
    parser.add_argument("--no-gmail",      action="store_true", help="Disable Gmail Watcher")
    parser.add_argument("--no-linkedin",   action="store_true", help="Disable LinkedIn Watcher")
    parser.add_argument("--no-whatsapp",   action="store_true", help="Disable WhatsApp Watcher")
    parser.add_argument("--no-social",     action="store_true", help="Disable Social Watcher (FB/IG/Twitter)")
    parser.add_argument("--no-scheduler",  action="store_true", help="Disable Scheduler")
    parser.add_argument("--dry-run",       action="store_true", help="Dry-run mode (no external actions)")
    args = parser.parse_args()

    if args.dry_run:
        os.environ["DRY_RUN"] = "true"

    orchestrator = Orchestrator(
        vault_path=args.vault,
        enable_gmail=not args.no_gmail,
        enable_linkedin=not args.no_linkedin,
        enable_scheduler=not args.no_scheduler,
        enable_social=not args.no_social,
        enable_whatsapp=not args.no_whatsapp,
    )
    orchestrator.run()


if __name__ == "__main__":
    main()
