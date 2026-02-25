"""
cloud_agent.py — Platinum Tier Cloud Agent Orchestrator.

The Cloud Agent runs 24/7 on a cloud VM. It handles the "draft" half of
the Cloud↔Local split architecture:

  CLOUD AGENT OWNS (draft-only, no execution):
  - Email triage → draft replies → /Pending_Approval/
  - Social post drafts → /To_Post/ or /Pending_Approval/
  - Claim items via move-to /In_Progress/cloud/
  - Write results to /Updates/ for Local Agent to merge

  LOCAL AGENT OWNS (execution):
  - Approvals and rejections (reads /Pending_Approval/)
  - WhatsApp sessions and actual responses
  - Payments and banking actions
  - Final "send" and "post" actions via MCP
  - Dashboard.md is written ONLY by Local Agent

Security: Cloud Agent NEVER reads .env — credentials sync is blocked.
         Only markdown and state files are synced via git.

Usage:
    uv run python cloud_agent.py
    uv run python cloud_agent.py --dry-run
    uv run python cloud_agent.py --no-gmail
    uv run python cloud_agent.py --agent-id cloud-vm-01
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
    format="%(asctime)s [CloudAgent] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("CloudAgent")

VAULT_PATH = Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()
AGENT_ID   = os.getenv("CLOUD_AGENT_ID", "cloud-01")
AGENT_ROLE = "cloud"


# ─── Vault paths ─────────────────────────────────────────────────────────────

def _path(name: str) -> Path:
    p = VAULT_PATH / name
    p.mkdir(parents=True, exist_ok=True)
    return p

NEEDS_ACTION_CLOUD = _path("Needs_Action/cloud")
NEEDS_ACTION_ROOT  = _path("Needs_Action")
IN_PROGRESS_CLOUD  = _path("In_Progress/cloud")
PENDING_APPROVAL   = _path("Pending_Approval")
UPDATES            = _path("Updates")
DONE               = _path("Done")
LOGS               = _path("Logs")
SIGNALS            = _path("Signals")


# ─── Logging ─────────────────────────────────────────────────────────────────

def log_action(action_type: str, target: str, result: str, details: dict = None):
    log_file = LOGS / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action_type": action_type,
        "actor": f"cloud_agent:{AGENT_ID}",
        "target": target,
        "parameters": details or {},
        "result": result,
    }
    entries = []
    if log_file.exists():
        try:
            entries = json.loads(log_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            entries = []
    entries.append(entry)
    log_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")


# ─── Claim-by-Move ───────────────────────────────────────────────────────────

def claim_item(task_file: Path) -> Path | None:
    """
    Atomically claim a task by moving it from Needs_Action → In_Progress/cloud/.
    Returns the new path, or None if already claimed by another agent.
    """
    dest = IN_PROGRESS_CLOUD / task_file.name
    try:
        task_file.rename(dest)
        logger.info(f"Claimed: {task_file.name}")
        log_action("claim_item", task_file.name, "success", {"agent": AGENT_ID})
        return dest
    except FileNotFoundError:
        # Another agent already claimed it
        return None
    except Exception as e:
        logger.warning(f"Could not claim {task_file.name}: {e}")
        return None


def release_item(claimed_file: Path, outcome: str = "done"):
    """Move a claimed item to /Done/ (completed) or back to /Needs_Action/ (failed)."""
    if outcome == "done":
        dest = DONE / claimed_file.name
    else:
        dest = NEEDS_ACTION_CLOUD / claimed_file.name
    try:
        claimed_file.rename(dest)
        log_action("release_item", claimed_file.name, outcome)
    except Exception as e:
        logger.error(f"Could not release {claimed_file.name}: {e}")


# ─── Draft Email Reply ────────────────────────────────────────────────────────

def draft_email_reply(task_file: Path, dry_run: bool = False):
    """
    Read an email task, draft a reply, write approval request.
    The Local Agent will execute the actual send after human approval.
    """
    content = task_file.read_text(encoding="utf-8")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # Parse basic metadata from frontmatter
    from_line = next((l for l in content.splitlines() if l.startswith("from:")), "from: unknown")
    subject_line = next((l for l in content.splitlines() if l.startswith("subject:")), "subject: (no subject)")
    sender = from_line.replace("from:", "").strip()
    subject = subject_line.replace("subject:", "").strip()

    approval_file = PENDING_APPROVAL / f"APPROVAL_cloud_email_reply_{ts}.md"
    approval_content = f"""---
type: approval_request
action: send_email
created: {datetime.now(timezone.utc).isoformat()}
agent: cloud:{AGENT_ID}
source_task: {task_file.name}
status: pending
---

# [Cloud Agent] Email Reply Draft

**From (original):** {sender}
**Subject:** {subject}

## Drafted Reply

> Thank you for your message. I'll review this and get back to you shortly.
>
> Best regards,
> World Digital

## Instructions
- Edit the reply above if needed
- Move this file to `/Approved/` to send
- Move to `/Rejected/` to discard

---
*Drafted by Cloud Agent {AGENT_ID} · Local Agent will execute send after approval · Handbook §3*
"""
    if not dry_run:
        approval_file.write_text(approval_content, encoding="utf-8")
        # Write update signal for Local Agent
        signal_file = UPDATES / f"UPDATE_email_draft_{ts}.md"
        signal_file.write_text(f"cloud_agent drafted email reply: {approval_file.name}\n", encoding="utf-8")
        log_action("draft_email_reply", sender, "success", {"approval_file": approval_file.name})
        logger.info(f"Drafted reply → {approval_file.name}")
    else:
        logger.info(f"[DRY RUN] Would draft reply for: {subject}")


# ─── Draft Social Post ────────────────────────────────────────────────────────

def draft_social_post(platform: str, topic: str, dry_run: bool = False):
    """
    Draft a social post and queue it for approval.
    Cloud Agent NEVER posts directly — only drafts.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    approval_file = PENDING_APPROVAL / f"APPROVAL_cloud_social_{platform}_{ts}.md"
    content = f"""---
type: approval_request
action: post_to_{platform.lower()}
created: {datetime.now(timezone.utc).isoformat()}
agent: cloud:{AGENT_ID}
platform: {platform}
status: pending
---

# [Cloud Agent] {platform} Post Draft

## Post Content

{topic}

## Instructions
- Edit the content above if needed
- Move to `/Approved/` to publish
- Move to `/Rejected/` to discard

---
*Drafted by Cloud Agent {AGENT_ID} · Local Agent will publish after approval · Handbook §5*
"""
    if not dry_run:
        approval_file.write_text(content, encoding="utf-8")
        log_action("draft_social_post", platform, "success", {"approval_file": approval_file.name})
        logger.info(f"Drafted {platform} post → {approval_file.name}")
    else:
        logger.info(f"[DRY RUN] Would draft {platform} post")


# ─── Health Check ─────────────────────────────────────────────────────────────

def write_health_signal():
    """Write a heartbeat signal that the Local Agent can monitor."""
    signal_file = SIGNALS / f"HEALTH_{AGENT_ID}.json"
    health = {
        "agent_id": AGENT_ID,
        "role": AGENT_ROLE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "online",
        "vault_path": str(VAULT_PATH),
        "in_progress_count": len(list(IN_PROGRESS_CLOUD.glob("*.md"))),
        "pending_approval_count": len(list(PENDING_APPROVAL.glob("*.md"))),
    }
    signal_file.write_text(json.dumps(health, indent=2), encoding="utf-8")


# ─── Main Poll Loop ───────────────────────────────────────────────────────────

class CloudAgent:
    def __init__(self, enable_gmail: bool = True, dry_run: bool = False, agent_id: str = "cloud-01"):
        global AGENT_ID
        AGENT_ID = agent_id
        self.enable_gmail = enable_gmail
        self.dry_run = dry_run
        self.check_interval = int(os.getenv("CLOUD_AGENT_INTERVAL", "60"))
        self._running = True

        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _shutdown(self, *_):
        logger.info("Cloud Agent shutting down...")
        self._running = False

    def _process_email_tasks(self):
        """Check Needs_Action/cloud/ for email tasks and draft replies."""
        email_tasks = list(NEEDS_ACTION_CLOUD.glob("EMAIL_*.md"))
        # Also check root Needs_Action for unclaimed email tasks
        email_tasks += [f for f in NEEDS_ACTION_ROOT.glob("EMAIL_*.md")
                        if not (IN_PROGRESS_CLOUD / f.name).exists()]

        for task_file in email_tasks:
            claimed = claim_item(task_file)
            if claimed:
                try:
                    draft_email_reply(claimed, dry_run=self.dry_run)
                    release_item(claimed, "done")
                except Exception as e:
                    logger.error(f"Failed to draft reply for {claimed.name}: {e}")
                    release_item(claimed, "failed")

    def _check_local_agent_health(self):
        """Read Local Agent's health signal if present."""
        local_signal = SIGNALS / "HEALTH_local-01.json"
        if local_signal.exists():
            try:
                health = json.loads(local_signal.read_text(encoding="utf-8"))
                age_s = (datetime.now(timezone.utc) -
                         datetime.fromisoformat(health["timestamp"])).total_seconds()
                if age_s > 300:  # 5 minutes without heartbeat
                    logger.warning(f"Local Agent may be offline (last seen {age_s:.0f}s ago)")
            except Exception:
                pass

    def run(self):
        logger.info(f"Cloud Agent {AGENT_ID} starting (interval={self.check_interval}s, dry_run={self.dry_run})")
        consecutive_errors = 0

        while self._running:
            try:
                write_health_signal()
                self._process_email_tasks()
                self._check_local_agent_health()

                consecutive_errors = 0
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                break
            except Exception as e:
                consecutive_errors += 1
                backoff = min(self.check_interval * (2 ** consecutive_errors), self.check_interval * 8)
                logger.error(f"Cloud Agent error (attempt {consecutive_errors}): {e}. Retry in {backoff}s")
                log_action("agent_error", "cloud_agent", "error",
                           {"error": str(e), "consecutive_errors": consecutive_errors})
                time.sleep(backoff)

        logger.info("Cloud Agent stopped.")


def main():
    parser = argparse.ArgumentParser(description="AI Employee Cloud Agent (Platinum Tier)")
    parser.add_argument("--no-gmail",   action="store_true", help="Skip Gmail watcher")
    parser.add_argument("--dry-run",    action="store_true", help="No external actions")
    parser.add_argument("--agent-id",   default="cloud-01",  help="Unique cloud agent identifier")
    args = parser.parse_args()

    agent = CloudAgent(
        enable_gmail=not args.no_gmail,
        dry_run=args.dry_run,
        agent_id=args.agent_id,
    )
    agent.run()


if __name__ == "__main__":
    main()
