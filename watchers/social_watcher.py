"""
social_watcher.py — Social Media Approval Queue Watcher (Gold Tier).

Watches /Approved/ for SOCIAL_{PLATFORM}_*.md files and creates
/Scheduled/TRIGGER_social_{platform}_{ts}.md files for Claude to publish
via Playwright MCP browser automation.

Same pattern as linkedin_watcher.py but parameterized for FB / IG / Twitter.

Usage:
    uv run social-watcher
    # or via orchestrator
"""

import os
import json
import time
import logging
import threading
import argparse
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SocialWatcher] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("SocialWatcher")

VAULT_PATH = Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()
APPROVED_DIR  = VAULT_PATH / "Approved"
SCHEDULED_DIR = VAULT_PATH / "Scheduled"
DONE_DIR      = VAULT_PATH / "Done"
LOGS_DIR      = VAULT_PATH / "Logs"

PLATFORMS = ["Facebook", "Instagram", "Twitter"]

# Playwright MCP login URLs per platform
PLATFORM_URLS = {
    "Facebook":  "https://www.facebook.com",
    "Instagram": "https://www.instagram.com",
    "Twitter":   "https://twitter.com/compose/tweet",
}


def _log(action_type: str, target: str, result: str, details: dict = None):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action_type": action_type,
        "actor": "social_watcher",
        "target": target,
        "parameters": details or {},
        "result": result,
    }
    entries = []
    if log_file.exists():
        try:
            entries = json.loads(log_file.read_text(encoding="utf-8"))
        except Exception:
            entries = []
    entries.append(entry)
    log_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")


class SocialWatcher:
    """
    Watches /Approved/ for SOCIAL_{PLATFORM}_*.md files.
    Creates /Scheduled/ trigger files for Claude to publish via Playwright MCP.
    """

    def __init__(self, vault_path: Path, platform: str, check_interval: int = 30):
        self.vault_path    = vault_path
        self.platform      = platform
        self.check_interval = check_interval
        self.approved_dir  = vault_path / "Approved"
        self.scheduled_dir = vault_path / "Scheduled"
        self.done_dir      = vault_path / "Done"
        self._seen: set[str] = set()
        self._running = True

        self.scheduled_dir.mkdir(parents=True, exist_ok=True)
        self.done_dir.mkdir(parents=True, exist_ok=True)

    def check_for_approved(self) -> list[Path]:
        """Scan /Approved/ for approved social posts for this platform."""
        pattern = f"SOCIAL_{self.platform.upper()}_*.md"
        found = []
        for f in sorted(self.approved_dir.glob(pattern)):
            if f.name not in self._seen:
                found.append(f)
        return found

    def create_trigger(self, approved_file: Path) -> Path:
        """
        Create a /Scheduled/TRIGGER_social_{platform}_{ts}.md file.
        Includes Playwright MCP instructions for the operator/Claude.
        """
        content = approved_file.read_text(encoding="utf-8")
        post_file = ""
        for line in content.split("\n"):
            if line.startswith("post_file:"):
                post_file = line.split(":", 1)[1].strip()
                break

        platform_url = PLATFORM_URLS.get(self.platform, "")
        skill_name = f"post-{self.platform.lower()}"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        trigger_file = self.scheduled_dir / f"TRIGGER_social_{self.platform.lower()}_{timestamp}.md"

        trigger_file.write_text(
            f"""---
type: social_trigger
platform: {self.platform}
approved_file: Approved/{approved_file.name}
post_file: {post_file}
created: {datetime.now(timezone.utc).isoformat()}
status: pending
---

# {self.platform} Post — Ready to Publish via Playwright MCP

Approved post is queued for {self.platform}. Run `/{skill_name}` to publish.

## Files
- Approved: `Approved/{approved_file.name}`
- Post content: `{post_file}`

## Playwright MCP Steps
1. Start Playwright MCP: `bash .claude/skills/browsing-with-playwright/scripts/start-server.sh`
2. Navigate to {platform_url}
3. Log in (use saved session from `secrets/{self.platform.lower()}_session/`)
4. Find the post creation area and enter the content
5. Submit the post
6. Confirm it's live — take a screenshot
7. Log success and move files to `/Done/`

## Action
Run: `/{skill_name}` → Step 7 (publish approved post via Playwright MCP browser tools)
""",
            encoding="utf-8",
        )

        _log("social_trigger_created", approved_file.name, "success", {
            "platform": self.platform,
            "trigger": trigger_file.name,
            "post_file": post_file,
        })
        logger.info(f"[{self.platform}] Trigger created: {trigger_file.name}")
        return trigger_file

    def run_once(self):
        """Process all pending approved posts for this platform."""
        for approved_file in self.check_for_approved():
            try:
                self.create_trigger(approved_file)
                self._seen.add(approved_file.name)
                # Move approved file to Done
                done_path = self.done_dir / approved_file.name
                approved_file.rename(done_path)
                logger.info(f"[{self.platform}] Archived: {approved_file.name}")
            except Exception as e:
                logger.error(f"[{self.platform}] Error processing {approved_file.name}: {e}")
                _log("social_trigger_error", approved_file.name, "error", {
                    "platform": self.platform, "error": str(e)
                })

    def run(self):
        """Continuous polling loop for this platform."""
        logger.info(f"[{self.platform}] Watcher started (interval: {self.check_interval}s)")
        while self._running:
            try:
                self.run_once()
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                logger.info(f"[{self.platform}] Watcher stopped.")
                break
            except Exception as e:
                logger.error(f"[{self.platform}] Watcher error: {e}")
                time.sleep(self.check_interval)

    def stop(self):
        self._running = False


def main():
    parser = argparse.ArgumentParser(description="Social Media Approval Queue Watcher (Gold Tier)")
    parser.add_argument("--vault", default=os.getenv("VAULT_PATH", "./AI_Employee_Vault"))
    parser.add_argument("--interval", type=int, default=30, help="Check interval in seconds")
    parser.add_argument("--platform", choices=PLATFORMS + ["all"], default="all",
                        help="Which platform to watch (default: all)")
    args = parser.parse_args()

    vault = Path(args.vault).resolve()

    if args.platform == "all":
        # Start a watcher thread for each platform
        watchers = [SocialWatcher(vault, p, args.interval) for p in PLATFORMS]
        threads = []
        for w in watchers:
            t = threading.Thread(target=w.run, daemon=True, name=f"SocialWatcher-{w.platform}")
            t.start()
            threads.append(t)
        logger.info(f"All platform watchers started: {PLATFORMS}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping all social watchers...")
            for w in watchers:
                w.stop()
    else:
        watcher = SocialWatcher(vault, args.platform, args.interval)
        try:
            watcher.run()
        except KeyboardInterrupt:
            logger.info(f"[{args.platform}] Watcher stopped.")


if __name__ == "__main__":
    main()
