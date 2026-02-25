"""
linkedin_watcher.py — Queue manager for LinkedIn posts.

Responsibilities:
  1. QUEUE MONITOR: Watch /Approved/LINKEDIN_POST_*.md for approved posts.
     → Creates a trigger in /Scheduled/ for Claude to publish via Playwright MCP.
     → Respects max 2 posts/day (Handbook §5 + LinkedIn Policy).

  2. NOTIFICATION WATCHER: Periodically create a trigger for Claude to check
     LinkedIn notifications via Playwright MCP.

Publishing is now handled by Claude Code using the Playwright MCP server:
  claude mcp add --transport stdio playwright npx @playwright/mcp@latest

The /post-linkedin skill uses browser_navigate / browser_click / browser_type
to post on LinkedIn — no local browser session needed.

Usage:
    uv run linkedin-watcher          # start queue monitor loop
"""

import os
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone, date
from dotenv import load_dotenv

from watchers.base_watcher import BaseWatcher

load_dotenv()


class LinkedInWatcher(BaseWatcher):
    """
    Monitors the LinkedIn post approval queue and creates Playwright MCP triggers.

    Handbook §5: Scheduled/pre-approved posts → auto-allowed after approval.
                 Replies and DMs → always require approval.
    LinkedIn Policy: Max 2 posts/day, business updates only.

    Publishing is delegated to Claude via the Playwright MCP server.
    """

    def __init__(self, vault_path: str, check_interval: int = 300):
        super().__init__(vault_path, check_interval=check_interval)
        self.to_post_dir = self.vault_path / "To_Post" / "LinkedIn"
        self.to_post_dir.mkdir(parents=True, exist_ok=True)
        self.scheduled_dir = self.vault_path / "Scheduled"
        self.scheduled_dir.mkdir(parents=True, exist_ok=True)
        self.dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
        self._posts_today_file = self.vault_path / ".linkedin_posts_today.json"
        self._posts_today: dict = self._load_posts_today()
        self._triggered: set = set()

    def _load_posts_today(self) -> dict:
        if self._posts_today_file.exists():
            try:
                data = json.loads(self._posts_today_file.read_text())
                if data.get("date") == str(date.today()):
                    return data
            except Exception:
                pass
        return {"date": str(date.today()), "count": 0, "posts": []}

    def _save_posts_today(self):
        self._posts_today_file.write_text(json.dumps(self._posts_today, indent=2), encoding='utf-8')

    def check_for_updates(self) -> list:
        """
        Returns approved LinkedIn post files that are ready to publish.
        The actual browser posting is done by Claude via Playwright MCP.
        """
        max_posts = int(os.getenv("LINKEDIN_MAX_POSTS_PER_DAY", "2"))
        today_count = self._posts_today.get("count", 0)

        if today_count >= max_posts:
            self.logger.info(f"Daily post limit reached ({today_count}/{max_posts}). Skipping.")
            return []

        approved_dir = self.vault_path / "Approved"
        queued = [
            f for f in sorted(approved_dir.glob("LINKEDIN_POST_*.md"))
            if f.name not in self._triggered
        ]

        remaining_slots = max_posts - today_count
        return queued[:remaining_slots]

    def create_action_file(self, approved_post: Path) -> Path:
        """
        Create a /Scheduled/ trigger so Claude publishes via Playwright MCP.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        trigger_file = self.scheduled_dir / f"TRIGGER_linkedin_post_{timestamp}.md"

        # Read post_file from the approved post's frontmatter
        content = approved_post.read_text(encoding='utf-8')
        post_file = ""
        for line in content.split("\n"):
            if line.startswith("post_file:"):
                post_file = line.split(":", 1)[1].strip()
                break

        trigger_file.write_text(
            f"""---
type: linkedin_trigger
approved_file: Approved/{approved_post.name}
post_file: {post_file}
created: {datetime.now(timezone.utc).isoformat()}
status: pending
---

# LinkedIn Post — Ready to Publish

An approved LinkedIn post is queued. Claude should run `/post-linkedin` to publish it
using the **Playwright MCP** browser tools.

## Approved File
`Approved/{approved_post.name}`

## Post Content File
`{post_file}`

## Instructions for Claude
1. Read the post content from `{post_file}`
2. Navigate to https://www.linkedin.com/feed/ via Playwright MCP
3. Use browser tools to open the post composer, type the content, and submit
4. Archive this trigger to /Done/ after successful posting
5. Log the action to /Logs/

## Action
Run: `/post-linkedin` (Step 7 - publish approved post via Playwright MCP)
""",
            encoding='utf-8',
        )

        self._triggered.add(approved_post.name)

        self.log_action("linkedin_trigger_created", approved_post.name, "success", {
            "trigger_file": trigger_file.name,
            "post_file": post_file,
        })
        self.logger.info(f"Trigger created for Claude to publish via Playwright MCP: {trigger_file.name}")
        return trigger_file

    def run(self):
        """Main loop: scan approved queue, create Playwright MCP triggers."""
        import time
        self.logger.info("LinkedIn Watcher started (Playwright MCP mode)")
        self.logger.info(f"Monitoring: /Approved/LINKEDIN_POST_*.md → /Scheduled/ triggers")
        self.logger.info("Publishing via: Playwright MCP (claude mcp add playwright)")
        self.logger.info("Press Ctrl+C to stop.")

        while True:
            try:
                items = self.check_for_updates()
                for item in items:
                    self.create_action_file(item)
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                self.logger.info("LinkedIn Watcher stopped.")
                break
            except Exception as e:
                self.logger.error(f"Loop error: {e}")
                time.sleep(self.check_interval)


def _run_setup(vault_path: str):
    """
    One-time LinkedIn setup:
    1. Creates secrets/linkedin_session/ directory (Playwright stores cookies here).
    2. Saves LinkedIn credentials to .env (used by Playwright MCP when logging in).
    3. Prints instructions for first login via Playwright MCP.
    """
    import getpass
    from pathlib import Path

    print("\n=== LinkedIn Watcher Setup ===\n")
    print("LinkedIn posting is done via Playwright MCP browser automation.")
    print("This setup saves your credentials so the AI can log in automatically.\n")

    # 1. Create session directory
    session_dir = Path(os.getenv("LINKEDIN_SESSION_PATH", "./secrets/linkedin_session"))
    session_dir.mkdir(parents=True, exist_ok=True)
    print(f"✓ Session directory created: {session_dir}")

    # 2. Save credentials to .env if not already set
    env_file = Path(".env")
    env_content = env_file.read_text(encoding="utf-8") if env_file.exists() else ""

    if "LINKEDIN_USER=" not in env_content or "LINKEDIN_USER=\n" in env_content:
        email = input("\nEnter your LinkedIn email: ").strip()
        if email:
            if "LINKEDIN_USER=" in env_content:
                lines = env_content.splitlines()
                env_content = "\n".join(
                    f"LINKEDIN_USER={email}" if l.startswith("LINKEDIN_USER=") else l
                    for l in lines
                ) + "\n"
            else:
                env_content += f"\nLINKEDIN_USER={email}\n"
            env_file.write_text(env_content, encoding="utf-8")
            print(f"✓ LINKEDIN_USER saved to .env")
    else:
        print("✓ LINKEDIN_USER already set in .env")

    if "LINKEDIN_PASSWORD=" not in env_content or "LINKEDIN_PASSWORD=\n" in env_content:
        password = getpass.getpass("Enter your LinkedIn password: ")
        if password:
            if "LINKEDIN_PASSWORD=" in env_content:
                lines = env_content.splitlines()
                env_content = "\n".join(
                    f"LINKEDIN_PASSWORD={password}" if l.startswith("LINKEDIN_PASSWORD=") else l
                    for l in lines
                ) + "\n"
            else:
                env_content += f"LINKEDIN_PASSWORD={password}\n"
            env_file.write_text(env_content, encoding="utf-8")
            print("✓ LINKEDIN_PASSWORD saved to .env")
    else:
        print("✓ LINKEDIN_PASSWORD already set in .env")

    # 3. Create a marker file so orchestrator knows setup is done
    marker = session_dir / ".setup_complete"
    marker.write_text(
        f"LinkedIn setup completed at {datetime.now(timezone.utc).isoformat()}\n",
        encoding="utf-8",
    )

    print("\n✓ Setup complete!\n")
    print("How LinkedIn posting works:")
    print("  1. You approve a post → move it to AI_Employee_Vault/Approved/")
    print("  2. Orchestrator creates a trigger file in AI_Employee_Vault/Scheduled/")
    print("  3. Run /post-linkedin in Claude Code — it uses Playwright MCP to log in and post")
    print(f"\nSession path: {session_dir.resolve()}")
    print("Run the watcher normally with: uv run linkedin-watcher\n")


def main():
    parser = argparse.ArgumentParser(description="AI Employee — LinkedIn Queue Watcher (Playwright MCP mode)")
    parser.add_argument("--vault",    default=os.getenv("VAULT_PATH", "./AI_Employee_Vault"))
    parser.add_argument("--interval", type=int, default=300)
    parser.add_argument("--setup",    action="store_true",
                        help="One-time setup: save LinkedIn credentials and create session directory")
    args = parser.parse_args()

    if args.setup:
        _run_setup(args.vault)
        return

    watcher = LinkedInWatcher(vault_path=args.vault, check_interval=args.interval)
    watcher.run()


if __name__ == "__main__":
    main()
