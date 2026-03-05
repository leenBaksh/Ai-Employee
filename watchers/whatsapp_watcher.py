"""
whatsapp_watcher.py — WhatsApp Web automation watcher (Playwright-based).

Monitors WhatsApp Web for unread messages containing priority keywords
and creates task files in /Needs_Action/ for each new message.

Architecture:
  - Playwright persistent context keeps the WhatsApp Web session alive
  - BaseWatcher loop polls every 30s for unread chats
  - Priority keywords trigger high-priority task files

Setup (one-time):
  1. Run with headless=False to scan the QR code:
       python -m watchers.whatsapp_watcher --setup
  2. Session is saved to secrets/whatsapp_session/
  3. Subsequent runs use the saved session (headless=True)

Usage:
    python -m watchers.whatsapp_watcher          # normal run
    python -m watchers.whatsapp_watcher --setup  # first-time QR login
    # or via orchestrator (starts automatically)
"""

import os
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

from watchers.base_watcher import BaseWatcher

load_dotenv()

URGENT_KEYWORDS = ["urgent", "asap", "invoice", "payment", "help",
                   "deadline", "action required", "emergency", "immediately"]


class WhatsAppWatcher(BaseWatcher):
    """
    Watches WhatsApp Web for unread messages via Playwright browser automation.

    Privacy (Handbook §6): Only stores message text (200 chars max),
    never full conversation history.
    """

    def __init__(self, vault_path: str, session_path: str = None,
                 check_interval: int = 30, headless: bool = True):
        super().__init__(vault_path, check_interval=check_interval)
        self.session_path = Path(
            session_path or os.getenv("WHATSAPP_SESSION_PATH", "./secrets/whatsapp_session")
        ).resolve()
        self.session_path.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self._seen_messages: set = self._load_seen()

    # ── Seen message dedup ────────────────────────────────────────────────────

    def _seen_file(self) -> Path:
        return self.vault_path / ".whatsapp_seen.json"

    def _load_seen(self) -> set:
        f = self._seen_file()
        if f.exists():
            try:
                return set(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                return set()
        return set()

    def _save_seen(self):
        # Keep only last 500 to prevent unbounded growth
        seen_list = list(self._seen_messages)[-500:]
        self._seen_file().write_text(json.dumps(seen_list, indent=2), encoding="utf-8")

    # ── Priority detection ────────────────────────────────────────────────────

    def _detect_priority(self, text: str) -> str:
        return "high" if any(kw in text.lower() for kw in URGENT_KEYWORDS) else "normal"

    # ── Playwright scraping ───────────────────────────────────────────────────

    def check_for_updates(self) -> list:
        """Open WhatsApp Web, find unread chats, return message dicts."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.logger.error("Playwright not installed — run: uv add playwright && playwright install chromium")
            return []

        messages = []

        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                str(self.session_path),
                headless=self.headless,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            try:
                page = browser.pages[0] if browser.pages else browser.new_page()
                page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")

                # Wait for chat list — if QR code appears, session expired
                try:
                    page.wait_for_selector('[data-testid="chat-list"]', timeout=20000)
                except Exception:
                    self.logger.error("WhatsApp Web not logged in — run with --setup to scan QR code")
                    self.log_action("whatsapp_poll", "WhatsApp Web", "error",
                                    {"error": "not logged in — QR scan required"})
                    return []

                # Find unread chats
                unread_chats = page.query_selector_all('[data-testid="cell-frame-container"]')

                for chat in unread_chats:
                    try:
                        # Check for unread badge
                        badge = chat.query_selector('[data-testid="icon-unread-count"]') or \
                                chat.query_selector('[aria-label*="unread"]')
                        if not badge:
                            continue

                        # Get sender name
                        name_el = chat.query_selector('[data-testid="cell-frame-title"]') or \
                                  chat.query_selector('span[title]')
                        sender_name = name_el.inner_text().strip() if name_el else "Unknown"

                        # Get message preview
                        preview_el = chat.query_selector('[data-testid="last-msg"]') or \
                                     chat.query_selector('span.x1iyjqo2')
                        text = preview_el.inner_text().strip()[:200] if preview_el else "(no preview)"

                        # Dedup key
                        dedup_key = f"{sender_name}:{text[:50]}"
                        if dedup_key in self._seen_messages:
                            continue

                        messages.append({
                            "sender_name": sender_name,
                            "text": text,
                            "dedup_key": dedup_key,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })

                    except Exception as e:
                        self.logger.warning(f"Error reading chat element: {e}")
                        continue

            finally:
                browser.close()

        self.logger.info(f"WhatsApp poll complete — {len(messages)} new message(s)")
        return messages

    # ── Vault task file ───────────────────────────────────────────────────────

    def create_action_file(self, message: dict) -> Path:
        """Create a task .md file for an incoming WhatsApp message."""
        sender_name = message["sender_name"]
        text        = message["text"]
        timestamp   = message["timestamp"]
        priority    = self._detect_priority(text)

        ts_slug     = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_name   = "".join(c if c.isalnum() or c in "-_" else "_" for c in sender_name)[:30]
        task_file   = self.needs_action / f"WHATSAPP_{ts_slug}_{safe_name}.md"

        task_file.write_text(
            f"""---
type: whatsapp_message
source: whatsapp_web
from_name: {sender_name}
received: {timestamp}
priority: {priority}
status: pending
---

## WhatsApp Message

**From:** {sender_name}
**Received:** {timestamp}

**Message:**
> {text}

## Detected Intent
{"⚠️ URGENT — contains urgent keyword" if priority == "high" else "Normal priority — standard review"}

## Suggested Actions
- [ ] Read full conversation in WhatsApp
- [ ] Draft reply (requires approval — Handbook §3)
- [ ] Forward to relevant team member if needed
- [ ] Archive after responding

## Notes
_Add context or decision here._

---
*Privacy note: Message preview truncated to 200 chars per Company Handbook §6*
""",
            encoding="utf-8",
        )

        # Mark as seen
        self._seen_messages.add(message["dedup_key"])
        self._save_seen()

        self.log_action("whatsapp_task_created", sender_name, "success", {
            "priority": priority,
            "task_file": task_file.name,
        })

        return task_file

    # ── Override run() ────────────────────────────────────────────────────────

    def run(self):
        self.logger.info("WhatsApp Watcher started (Playwright/WhatsApp Web mode)")
        self.logger.info(f"Session path: {self.session_path}")
        self.logger.info(f"Headless: {self.headless}")
        super().run()


# ── Setup helper ──────────────────────────────────────────────────────────────

def _run_setup(vault_path: str):
    """Open WhatsApp Web with a visible browser so user can scan the QR code."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not installed. Run: uv add playwright && playwright install chromium")
        return

    session_path = Path(os.getenv("WHATSAPP_SESSION_PATH", "./secrets/whatsapp_session")).resolve()
    session_path.mkdir(parents=True, exist_ok=True)

    print("\n=== WhatsApp Watcher Setup ===\n")
    print("A browser window will open. Scan the QR code with your phone.")
    print("Once logged in, press Enter here to save the session.\n")
    print(f"Session will be saved to: {session_path}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            str(session_path),
            headless=False,
        )
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto("https://web.whatsapp.com")
        print("Browser opened. Scan the QR code on your phone...")
        input("\nPress Enter after you are logged in to save the session: ")
        browser.close()

    print("\nSession saved! Run the watcher normally with:")
    print("  python -m watchers.whatsapp_watcher\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AI Employee — WhatsApp Web Watcher (Playwright)")
    parser.add_argument("--vault",    default=os.getenv("VAULT_PATH", "./AI_Employee_Vault"))
    parser.add_argument("--session",  default=os.getenv("WHATSAPP_SESSION_PATH", "./secrets/whatsapp_session"))
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--no-headless", action="store_true", help="Show browser window")
    parser.add_argument("--setup",    action="store_true", help="First-time QR code login")
    args = parser.parse_args()

    if args.setup:
        _run_setup(args.vault)
        return

    watcher = WhatsAppWatcher(
        vault_path=args.vault,
        session_path=args.session,
        check_interval=args.interval,
        headless=not args.no_headless,
    )
    watcher.run()


if __name__ == "__main__":
    main()
