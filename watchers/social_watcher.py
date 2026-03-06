"""
social_watcher.py — Social Media Approval Queue Watcher (Gold Tier).

Watches /Approved/ for SOCIAL_{PLATFORM}_*.md files and creates
/Scheduled/TRIGGER_social_{platform}_{ts}.md files for Claude to publish
via Playwright MCP browser automation.

Follows the BaseWatcher pattern (check_for_updates / create_action_file).

Usage:
    uv run social-watcher
    # or via orchestrator
"""

import os
import time
import logging
import threading
import argparse
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

from watchers.base_watcher import BaseWatcher

load_dotenv()

# Playwright MCP login URLs per platform
PLATFORM_URLS = {
    "Facebook":  "https://www.facebook.com",
    "Instagram": "https://www.instagram.com",
    "Twitter":   "https://twitter.com/compose/tweet",
}

PLATFORMS = ["Facebook", "Instagram", "Twitter"]

logger = logging.getLogger("SocialWatcher")


class SocialWatcher(BaseWatcher):
    """
    Watches /Approved/ for SOCIAL_{PLATFORM}_*.md files.
    Creates /Scheduled/ trigger files for Claude to publish via Playwright MCP.

    Follows BaseWatcher pattern:
      check_for_updates() → approved social posts for this platform
      create_action_file() → /Scheduled/TRIGGER_social_{platform}_{ts}.md
    """

    def __init__(self, vault_path: str, platform: str, check_interval: int = 30):
        super().__init__(vault_path, check_interval)
        self.platform      = platform
        self.approved_dir  = self.vault_path / "Approved"
        self.scheduled_dir = self.vault_path / "Scheduled"
        self._seen: set[str] = set()
        self._ensure_social_dirs()

    def _ensure_social_dirs(self):
        for d in [self.approved_dir, self.scheduled_dir, self.done]:
            d.mkdir(parents=True, exist_ok=True)

    @property
    def done(self) -> Path:
        return self.vault_path / "Done"

    # ── BaseWatcher interface ─────────────────────────────────────────────────

    def check_for_updates(self) -> list:
        """Return approved social post files for this platform not yet processed."""
        pattern = f"SOCIAL_{self.platform.upper()}_*.md"
        return [
            f for f in sorted(self.approved_dir.glob(pattern))
            if f.name not in self._seen
        ]

    def create_action_file(self, item: Path) -> Path:
        """
        Create /Scheduled/TRIGGER_social_{platform}_{ts}.md from an approved post.
        Moves the approved file to /Done/ after trigger creation.
        """
        approved_file = item
        content = approved_file.read_text(encoding="utf-8")
        post_file = ""
        for line in content.split("\n"):
            if line.startswith("post_file:"):
                post_file = line.split(":", 1)[1].strip()
                break

        platform_url = PLATFORM_URLS.get(self.platform, "")
        skill_name   = f"post-{self.platform.lower()}"
        ts           = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        trigger_file = self.scheduled_dir / f"TRIGGER_social_{self.platform.lower()}_{ts}.md"

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

        self.log_action("social_trigger_created", approved_file.name, "success", {
            "platform": self.platform,
            "trigger": trigger_file.name,
            "post_file": post_file,
        })

        # Mark seen and archive approved file
        self._seen.add(approved_file.name)
        approved_file.rename(self.done / approved_file.name)
        self.logger.info(f"[{self.platform}] Archived: {approved_file.name}")

        return trigger_file


def main():
    parser = argparse.ArgumentParser(description="Social Media Approval Queue Watcher (Gold Tier)")
    parser.add_argument("--vault",     default=os.getenv("VAULT_PATH", "./AI_Employee_Vault"))
    parser.add_argument("--interval",  type=int, default=30, help="Check interval in seconds")
    parser.add_argument("--platform",  choices=PLATFORMS + ["all"], default="all",
                        help="Which platform to watch (default: all)")
    args = parser.parse_args()

    if args.platform == "all":
        watchers = [SocialWatcher(args.vault, p, args.interval) for p in PLATFORMS]
        threads  = [
            threading.Thread(target=w.run, daemon=True, name=f"SocialWatcher-{w.platform}")
            for w in watchers
        ]
        for t in threads:
            t.start()
        logger.info(f"All platform watchers started: {PLATFORMS}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping all social watchers...")
    else:
        SocialWatcher(args.vault, args.platform, args.interval).run()


if __name__ == "__main__":
    main()
