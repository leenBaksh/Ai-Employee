"""
gmail_watcher.py — Monitors Gmail for unread important emails.

For each unread/important email:
  1. Creates a .md task file in /Needs_Action/ with email metadata (snippet only — §6 privacy)
  2. Marks the message as processed (stores ID in local state)
  3. Logs the event

OAuth2 Setup (one-time):
  1. Go to Google Cloud Console → Enable Gmail API
  2. Create OAuth credentials (Desktop app) → Download as credentials.json
  3. Set GMAIL_CREDENTIALS_PATH and GMAIL_TOKEN_PATH in .env
  4. First run will open browser for authorization

Usage:
    uv run gmail-watcher
    # or:
    python -m watchers.gmail_watcher
"""

import os
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

from watchers.base_watcher import BaseWatcher

load_dotenv()


def _is_wsl() -> bool:
    """Detect if running inside WSL (Windows Subsystem for Linux)."""
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except Exception:
        return False


def _open_windows_browser(url: str):
    """Open a URL in the Windows default browser from inside WSL2."""
    import subprocess
    try:
        # cmd.exe /c start "" <url>  — opens default Windows browser
        subprocess.Popen(
            ["cmd.exe", "/c", "start", "", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except FileNotFoundError:
        return False


def _oauth_wsl2(flow):
    """
    WSL2-compatible OAuth2 flow.
    Opens Windows browser via cmd.exe, runs local server on fixed port 8085
    (WSL2 → Windows localhost forwarding works for the callback).
    """
    WSL2_PORT = 8085
    flow.redirect_uri = f"http://localhost:{WSL2_PORT}/"
    auth_url, _ = flow.authorization_url(prompt="consent")

    print(f"\nOpening Windows browser for Google authorization...")
    opened = _open_windows_browser(auth_url)

    if not opened:
        print("Could not open browser automatically. Open this URL manually:\n")
        print(f"  {auth_url}\n")
    else:
        print("Browser opened! Log in to Google and click Allow.")

    print(f"Waiting for authorization on port {WSL2_PORT}...\n")

    creds = flow.run_local_server(
        port=WSL2_PORT,
        open_browser=False,
        success_message="Authorization complete! You can close this tab.",
    )
    return creds


def _build_gmail_service(credentials_path: str, token_path: str):
    """Build and return an authenticated Gmail API service."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError("Gmail dependencies not installed. Run: uv sync")

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    creds = None
    token = Path(token_path)

    if token.exists():
        creds = Credentials.from_authorized_user_file(str(token), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            if _is_wsl():
                creds = _oauth_wsl2(flow)
            else:
                creds = flow.run_local_server(port=0)
        token.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


class GmailWatcher(BaseWatcher):
    """
    Polls Gmail for unread important emails and creates task files.

    Privacy (Handbook §6): Only stores email snippets (150 chars max),
    never full email bodies.
    """

    URGENT_KEYWORDS = ["urgent", "asap", "invoice", "payment", "help", "deadline", "action required"]

    def __init__(self, vault_path: str, credentials_path: str, token_path: str,
                 check_interval: int = 120, watch_labels: list[str] = None):
        super().__init__(vault_path, check_interval=check_interval)
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.watch_labels = watch_labels or ["INBOX", "IMPORTANT"]
        self._processed_ids: set[str] = self._load_processed_ids()
        self._service = None
        self.dry_run = os.getenv("DRY_RUN", "false").lower() == "true"

    def _processed_ids_file(self) -> Path:
        return self.vault_path / ".gmail_processed_ids.json"

    def _load_processed_ids(self) -> set[str]:
        f = self._processed_ids_file()
        if f.exists():
            try:
                return set(json.loads(f.read_text()))
            except Exception:
                return set()
        return set()

    def _save_processed_ids(self):
        self._processed_ids_file().write_text(
            json.dumps(list(self._processed_ids), indent=2)
        )

    def _get_service(self):
        if self._service is None:
            self._service = _build_gmail_service(self.credentials_path, self.token_path)
        return self._service

    def _detect_priority(self, subject: str, snippet: str) -> str:
        text = f"{subject} {snippet}".lower()
        return "high" if any(kw in text for kw in self.URGENT_KEYWORDS) else "normal"

    def check_for_updates(self) -> list:
        """Fetch unread important emails not yet processed."""
        if self.dry_run:
            self.logger.info("[DRY RUN] Skipping Gmail API call")
            return []

        try:
            service = self._get_service()
            query = "is:unread " + " OR ".join(f"label:{l}" for l in self.watch_labels)
            result = service.users().messages().list(userId="me", q=query, maxResults=20).execute()
            messages = result.get("messages", [])
            new = [m for m in messages if m["id"] not in self._processed_ids]
            if new:
                self.logger.info(f"Found {len(new)} new email(s)")
            return new
        except Exception as e:
            self.logger.error(f"Gmail API error: {e}")
            self.log_action("gmail_poll", "Gmail API", "error", {"error": str(e)})
            return []

    def create_action_file(self, message: dict) -> Path:
        """Create a task .md file for a Gmail message."""
        try:
            service = self._get_service()
            msg = service.users().messages().get(
                userId="me", id=message["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()
        except Exception as e:
            self.logger.error(f"Failed to fetch message {message['id']}: {e}")
            raise

        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        snippet = msg.get("snippet", "")[:150]  # §6: snippets only, max 150 chars
        subject = headers.get("Subject", "No Subject")
        sender = headers.get("From", "Unknown")
        date = headers.get("Date", datetime.now(timezone.utc).isoformat())
        priority = self._detect_priority(subject, snippet)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        # Sanitize for filename
        safe_subject = "".join(c if c.isalnum() or c in "-_" else "_" for c in subject)[:40]
        task_file = self.needs_action / f"EMAIL_{timestamp}_{safe_subject}.md"

        task_file.write_text(
            f"""---
type: email
source: gmail
message_id: {message["id"]}
from: {sender}
subject: {subject}
date: {date}
received: {datetime.now(timezone.utc).isoformat()}
priority: {priority}
status: pending
---

## Email Summary

**From:** {sender}
**Subject:** {subject}
**Date:** {date}

**Snippet:** _{snippet}_

## Detected Intent
{"⚠️ URGENT — contains urgent keyword" if priority == "high" else "Normal priority — standard review"}

## Suggested Actions
- [ ] Read full email in Gmail
- [ ] Draft reply (requires approval — Handbook §3)
- [ ] Forward to relevant party if needed
- [ ] Archive after processing

## Notes
_Add context or decision here._

---
*Privacy note: Full email body not stored per Company Handbook §6*
"""
        )

        self._processed_ids.add(message["id"])
        self._save_processed_ids()

        self.log_action("email_task_created", sender, "success", {
            "message_id": message["id"],
            "subject": subject,
            "priority": priority,
            "task_file": task_file.name,
        })
        return task_file


def _run_setup(credentials_path: str, token_path: str):
    """
    One-time Gmail OAuth2 setup.
    If credentials.json exists: opens browser to authorize and saves the token.
    If credentials.json is missing: prints step-by-step instructions.
    """
    creds_file = Path(credentials_path)
    token_file = Path(token_path)

    print("\n=== Gmail Watcher Setup ===\n")

    if not creds_file.exists():
        print("WARNING: credentials.json not found.\n")
        print("Follow these steps to get it:\n")
        print("  1. Go to: https://console.cloud.google.com/")
        print("  2. Select your project (or create one)")
        print("  3. Go to: APIs & Services -> Library")
        print("  4. Search 'Gmail API' -> Enable it")
        print("  5. Go to: APIs & Services -> Credentials")
        print("  6. Click 'Create Credentials' -> 'OAuth client ID'")
        print("  7. Application type: Desktop app -> Create")
        print("  8. Click Download (arrow) -> save as: secrets/gmail_credentials.json")
        print(f"\n  Save to: {creds_file.resolve()}")
        print("\nThen re-run: uv run gmail-watcher --setup\n")
        return

    print(f"OK: Found credentials.json at: {creds_file}")

    if _is_wsl():
        print("\nWSL2 detected - using manual copy-paste auth flow.")
        print("You will be shown a URL to open in Windows browser,")
        print("then asked to paste the redirect URL back here.\n")
    else:
        print("\nOpening browser for Google authorization...")
        print("(A browser window will open - log in and allow access)\n")

    try:
        # Ensure secrets/ directory exists
        token_file.parent.mkdir(parents=True, exist_ok=True)

        # This triggers the OAuth2 browser flow and saves the token
        service = _build_gmail_service(str(creds_file), str(token_file))

        # Quick test - list labels to confirm it works
        result = service.users().labels().list(userId="me").execute()
        label_count = len(result.get("labels", []))

        print(f"\nOK: Authorization successful!")
        print(f"OK: Token saved to: {token_file.resolve()}")
        print(f"OK: Gmail connected - found {label_count} labels")
        print("\nSetup complete! Run the watcher with: uv run gmail-watcher\n")

    except Exception as e:
        print(f"\nERROR: Authorization failed: {e}")
        print("Check that your credentials.json is valid and try again.\n")


def main():
    parser = argparse.ArgumentParser(description="AI Employee — Gmail Watcher")
    parser.add_argument("--vault",        default=os.getenv("VAULT_PATH", "./AI_Employee_Vault"))
    parser.add_argument("--credentials",  default=os.getenv("GMAIL_CREDENTIALS_PATH", "./secrets/gmail_credentials.json"))
    parser.add_argument("--token",        default=os.getenv("GMAIL_TOKEN_PATH", "./secrets/gmail_token.json"))
    parser.add_argument("--interval",     type=int, default=int(os.getenv("GMAIL_CHECK_INTERVAL", "120")))
    parser.add_argument("--setup",        action="store_true",
                        help="One-time OAuth2 setup: authorize Gmail access and save token")
    args = parser.parse_args()

    if args.setup:
        _run_setup(args.credentials, args.token)
        return

    creds = Path(args.credentials)
    if not creds.exists():
        print(f"\n⚠️  Gmail credentials not found at: {creds}")
        print("Run setup first: uv run gmail-watcher --setup\n")
        return

    watcher = GmailWatcher(
        vault_path=args.vault,
        credentials_path=args.credentials,
        token_path=args.token,
        check_interval=args.interval,
    )
    watcher.run()


if __name__ == "__main__":
    main()
