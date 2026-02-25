"""
whatsapp_watcher.py — WhatsApp Business Cloud API watcher.

Receives incoming WhatsApp messages via Meta webhook and creates
task files in /Needs_Action/ for each new message.

Architecture:
  - Flask webhook server runs in a background thread (receives push events from Meta)
  - Messages are queued thread-safely
  - BaseWatcher loop drains the queue and calls create_action_file()

Meta WhatsApp Business Cloud API Setup (one-time):
  1. Go to developers.facebook.com → Create App → Business type
  2. Add "WhatsApp" product to your app
  3. Go to WhatsApp → Configuration → set webhook URL and verify token
  4. Webhook URL: http://<your-public-ip>:8089/webhook  (use ngrok for local dev)
  5. Subscribe to: messages
  6. Copy Phone Number ID and generate a permanent access token
  7. Set WHATSAPP_VERIFY_TOKEN, WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID in .env

Usage:
    uv run whatsapp-watcher
    uv run whatsapp-watcher --setup
    # or via orchestrator (starts automatically)
"""

import os
import json
import queue
import threading
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("WhatsAppWatcher")

try:
    from flask import Flask, request, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

from watchers.base_watcher import BaseWatcher


URGENT_KEYWORDS = ["urgent", "asap", "invoice", "payment", "help",
                   "deadline", "action required", "emergency", "immediately"]


class WhatsAppWatcher(BaseWatcher):
    """
    Watches for incoming WhatsApp Business messages via Meta webhook.

    Privacy (Handbook §6): Only stores message text (200 chars max),
    never full conversation history.
    """

    def __init__(self, vault_path: str, check_interval: int = 5,
                 webhook_port: int = 8089):
        super().__init__(vault_path, check_interval=check_interval)
        self.webhook_port = webhook_port
        self.verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
        self.dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
        self._message_queue: queue.Queue = queue.Queue()
        self._processed_ids: set[str] = self._load_processed_ids()
        self._flask_thread: threading.Thread | None = None

    def _processed_ids_file(self) -> Path:
        return self.vault_path / ".whatsapp_processed_ids.json"

    def _load_processed_ids(self) -> set[str]:
        f = self._processed_ids_file()
        if f.exists():
            try:
                return set(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                return set()
        return set()

    def _save_processed_ids(self):
        self._processed_ids_file().write_text(
            json.dumps(list(self._processed_ids), indent=2), encoding="utf-8"
        )

    def _detect_priority(self, text: str, sender_name: str) -> str:
        combined = f"{text} {sender_name}".lower()
        return "high" if any(kw in combined for kw in URGENT_KEYWORDS) else "normal"

    # ── Flask Webhook Server ──────────────────────────────────────────────────

    def _build_flask_app(self) -> "Flask":
        app = Flask(__name__)
        # Disable Flask's default logging to avoid duplicate log lines
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.WARNING)

        @app.get("/webhook")
        def verify():
            """Meta webhook verification handshake."""
            mode      = request.args.get("hub.mode")
            token     = request.args.get("hub.verify_token")
            challenge = request.args.get("hub.challenge")

            if mode == "subscribe" and token == self.verify_token:
                logger.info("WhatsApp webhook verified by Meta")
                return challenge, 200
            logger.warning("Webhook verification failed — check WHATSAPP_VERIFY_TOKEN")
            return "Forbidden", 403

        @app.post("/webhook")
        def receive():
            """Receive incoming message events from Meta."""
            data = request.get_json(silent=True) or {}

            # Walk the nested Meta payload structure
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages  = value.get("messages", [])
                    contacts  = {c["wa_id"]: c.get("profile", {}).get("name", "Unknown")
                                 for c in value.get("contacts", [])}

                    for msg in messages:
                        msg_id = msg.get("id", "")
                        if msg_id in self._processed_ids:
                            continue

                        # Only handle text messages (extend for media/template if needed)
                        msg_type = msg.get("type", "")
                        if msg_type == "text":
                            text = msg.get("text", {}).get("body", "")
                        elif msg_type == "button":
                            text = msg.get("button", {}).get("text", "(button reply)")
                        else:
                            text = f"(unsupported message type: {msg_type})"

                        sender_id   = msg.get("from", "unknown")
                        sender_name = contacts.get(sender_id, "Unknown")
                        timestamp   = msg.get("timestamp", "")

                        self._message_queue.put({
                            "id":          msg_id,
                            "from":        sender_id,
                            "name":        sender_name,
                            "text":        text[:200],   # §6: max 200 chars
                            "type":        msg_type,
                            "timestamp":   timestamp,
                            "raw_payload": {},           # §6: no full body stored
                        })
                        logger.info(f"Message queued from {sender_name} ({sender_id})")

            return jsonify({"status": "ok"}), 200

        return app

    def _start_webhook_server(self):
        """Start the Flask server in a daemon thread."""
        if not FLASK_AVAILABLE:
            logger.error("Flask not installed — run: uv sync")
            return

        if self.dry_run:
            logger.info("[DRY RUN] Webhook server not started")
            return

        if not self.verify_token:
            logger.warning("WHATSAPP_VERIFY_TOKEN not set — webhook verification will fail")

        app = self._build_flask_app()
        self._flask_thread = threading.Thread(
            target=lambda: app.run(
                host="0.0.0.0",
                port=self.webhook_port,
                debug=False,
                use_reloader=False,
            ),
            daemon=True,
            name="WhatsApp-Webhook",
        )
        self._flask_thread.start()
        logger.info(f"WhatsApp webhook server started on port {self.webhook_port}")
        logger.info(f"  → Webhook URL: http://0.0.0.0:{self.webhook_port}/webhook")
        logger.info("  → For public access: ngrok http " + str(self.webhook_port))

    # ── BaseWatcher interface ─────────────────────────────────────────────────

    def check_for_updates(self) -> list:
        """Drain the message queue — return all pending messages."""
        if self.dry_run:
            return []

        messages = []
        while not self._message_queue.empty():
            try:
                messages.append(self._message_queue.get_nowait())
            except queue.Empty:
                break
        return messages

    def create_action_file(self, message: dict) -> Path:
        """Create a task .md file for an incoming WhatsApp message."""
        msg_id      = message["id"]
        sender_id   = message["from"]
        sender_name = message["name"]
        text        = message["text"]
        msg_type    = message["type"]
        priority    = self._detect_priority(text, sender_name)

        ts_raw      = message.get("timestamp", "")
        try:
            received_dt = datetime.fromtimestamp(int(ts_raw), tz=timezone.utc).isoformat()
        except (ValueError, TypeError):
            received_dt = datetime.now(timezone.utc).isoformat()

        timestamp   = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_name   = "".join(c if c.isalnum() or c in "-_" else "_" for c in sender_name)[:30]
        task_file   = self.needs_action / f"WHATSAPP_{timestamp}_{safe_name}.md"

        task_file.write_text(
            f"""---
type: whatsapp_message
source: whatsapp_business
message_id: {msg_id}
from_number: {sender_id}
from_name: {sender_name}
received: {received_dt}
message_type: {msg_type}
priority: {priority}
status: pending
---

## WhatsApp Message

**From:** {sender_name} (+{sender_id})
**Received:** {received_dt}

**Message:**
> {text}

## Detected Intent
{"⚠️ URGENT — contains urgent keyword" if priority == "high" else "Normal priority — standard review"}

## Suggested Actions
- [ ] Read full conversation in WhatsApp Business app
- [ ] Draft reply (requires approval — Handbook §3)
- [ ] Forward to relevant team member if needed
- [ ] Archive after responding

## Notes
_Add context or decision here._

---
*Privacy note: Full message text truncated to 200 chars per Company Handbook §6*
""",
            encoding="utf-8",
        )

        self._processed_ids.add(msg_id)
        self._save_processed_ids()

        self.log_action("whatsapp_task_created", sender_name, "success", {
            "message_id": msg_id,
            "from": sender_id,
            "priority": priority,
            "task_file": task_file.name,
        })
        return task_file

    # ── Override run() to start webhook server first ──────────────────────────

    def run(self):
        """Start webhook server then enter the BaseWatcher polling loop."""
        self._start_webhook_server()
        super().run()


# ── Setup helper ─────────────────────────────────────────────────────────────

def _run_setup():
    """Print step-by-step Meta WhatsApp Business Cloud API setup instructions."""
    print("\n=== WhatsApp Business Watcher Setup ===\n")
    print("This watcher uses the Meta WhatsApp Business Cloud API (free tier).")
    print("You need a Meta Developer account and a WhatsApp Business Phone Number.\n")
    print("Step 1 — Create a Meta App")
    print("  1. Go to: https://developers.facebook.com/apps/")
    print("  2. Click 'Create App' → Choose 'Business' → Name it 'AI Employee'")
    print("  3. Add the 'WhatsApp' product to your app\n")
    print("Step 2 — Get your credentials")
    print("  4. WhatsApp → API Setup:")
    print("     - Copy 'Phone Number ID' → set WHATSAPP_PHONE_NUMBER_ID in .env")
    print("     - Generate a permanent access token → set WHATSAPP_ACCESS_TOKEN in .env")
    print("  5. Create a verify token (any string) → set WHATSAPP_VERIFY_TOKEN in .env\n")
    print("Step 3 — Expose your local server (WSL2 / local machine)")
    print("  6. Install ngrok: https://ngrok.com/download")
    print("  7. Run: ngrok http 8089")
    print("  8. Copy the https:// URL (e.g. https://abc123.ngrok.io)\n")
    print("Step 4 — Register webhook with Meta")
    print("  9. WhatsApp → Configuration → Webhooks")
    print("  10. Callback URL: https://abc123.ngrok.io/webhook")
    print("  11. Verify Token: <your WHATSAPP_VERIFY_TOKEN>")
    print("  12. Subscribe to: 'messages'\n")
    print("Step 5 — Add your .env values")
    print("  WHATSAPP_VERIFY_TOKEN=your_verify_token")
    print("  WHATSAPP_ACCESS_TOKEN=your_permanent_access_token")
    print("  WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id\n")
    print("Step 6 — Start the watcher")
    print("  uv run whatsapp-watcher\n")
    print("Test by sending a WhatsApp message to your Business number.")
    print("A task file will appear in AI_Employee_Vault/Needs_Action/\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AI Employee — WhatsApp Business Watcher")
    parser.add_argument("--vault",    default=os.getenv("VAULT_PATH", "./AI_Employee_Vault"))
    parser.add_argument("--port",     type=int, default=int(os.getenv("WHATSAPP_WEBHOOK_PORT", "8089")))
    parser.add_argument("--interval", type=int, default=5,
                        help="Queue drain interval in seconds (default: 5)")
    parser.add_argument("--setup",    action="store_true",
                        help="Print step-by-step Meta API setup instructions")
    args = parser.parse_args()

    if args.setup:
        _run_setup()
        return

    watcher = WhatsAppWatcher(
        vault_path=args.vault,
        check_interval=args.interval,
        webhook_port=args.port,
    )
    watcher.run()


if __name__ == "__main__":
    main()
