"""
whatsapp_webhook_server.py — WhatsApp Business Cloud API Webhook Server.

Receives inbound WhatsApp messages via Meta's Cloud API webhook and creates
task files in /Needs_Action/ for Claude to process.

Architecture:
  - Flask HTTP server on port 8089 (configurable via WHATSAPP_WEBHOOK_PORT)
  - Verifies webhook with Meta using VERIFY_TOKEN
  - Receives message events from Meta Graph API
  - Creates WHATSAPP_*.md files in /Needs_Action/ (same format as whatsapp_watcher.py)
  - Supports auto-reply acknowledgement (configurable via WHATSAPP_AUTO_REPLY)

Setup:
  1. Configure .env:
     - WHATSAPP_VERIFY_TOKEN=your_verify_token
     - WHATSAPP_ACCESS_TOKEN=your_meta_access_token
     - WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
     - WHATSAPP_WEBHOOK_PORT=8089
     - WHATSAPP_AUTO_REPLY=true (optional)
     - WHATSAPP_AUTO_REPLY_MESSAGE="Thanks for your message..." (optional)

  2. In Meta Developer Portal, set webhook URL:
     https://your-domain.com/webhook (or use ngrok for local dev)

  3. Start server: uv run whatsapp-webhook

Usage:
    uv run whatsapp-webhook              # start webhook server
    uv run whatsapp-webhook --test       # run self-test after startup
"""

import os
import sys
import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from watchers.base_watcher import BaseWatcher

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────

VAULT_PATH = Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()
NEEDS_ACTION = VAULT_PATH / "Needs_Action"

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WEBHOOK_PORT = int(os.getenv("WHATSAPP_WEBHOOK_PORT", "8089"))

AUTO_REPLY_ENABLED = os.getenv("WHATSAPP_AUTO_REPLY", "false").lower() == "true"
AUTO_REPLY_MESSAGE = os.getenv(
    "WHATSAPP_AUTO_REPLY_MESSAGE",
    "Thanks for your message! Our AI Employee has received it and will follow up shortly."
)

# ── Dynamic Token Reload ──────────────────────────────────────────────────────

def _get_env_from_file(key: str, default: str = "") -> str:
    """Get an environment variable from .env file (reloads on each call)."""
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        content = env_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
    return os.getenv(key, default)

def _get_current_access_token() -> str:
    """Get the current access token from .env file (reloads on each call)."""
    return _get_env_from_file("WHATSAPP_ACCESS_TOKEN", "")

def _get_current_phone_number_id() -> str:
    """Get the current phone number ID from .env file (reloads on each call)."""
    return _get_env_from_file("WHATSAPP_PHONE_NUMBER_ID", "")

# Deduplication: store message IDs we've already processed
SEEN_FILE = VAULT_PATH / ".whatsapp_webhook_seen.json"
_seen_message_ids: set = set()


def _load_seen():
    """Load previously seen message IDs to prevent duplicates."""
    global _seen_message_ids
    if SEEN_FILE.exists():
        try:
            _seen_message_ids = set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))
        except Exception:
            _seen_message_ids = set()


def _save_seen():
    """Save seen message IDs, keeping only last 500."""
    seen_list = list(_seen_message_ids)[-500:]
    SEEN_FILE.write_text(json.dumps(seen_list, indent=2), encoding="utf-8")


def _detect_priority(text: str) -> str:
    """Detect message priority based on keywords."""
    URGENT_KEYWORDS = [
        "urgent", "asap", "invoice", "payment", "help",
        "deadline", "action required", "emergency", "immediately"
    ]
    return "high" if any(kw in text.lower() for kw in URGENT_KEYWORDS) else "normal"


def _create_task_file(message_data: dict) -> Path:
    """Create a task .md file for an incoming WhatsApp message."""
    NEEDS_ACTION.mkdir(parents=True, exist_ok=True)

    sender_name = message_data.get("sender_name", "Unknown")
    text = message_data.get("text", "")
    timestamp = message_data.get("timestamp", datetime.now(timezone.utc).isoformat())
    priority = _detect_priority(text)
    wa_id = message_data.get("wa_id", "")
    chat_info = message_data.get("chat_info", {})

    ts_slug = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in sender_name)[:30]
    task_file = NEEDS_ACTION / f"WHATSAPP_{ts_slug}_{safe_name}.md"

    # Extract chat status
    is_group = chat_info.get("is_group", False)
    is_read = chat_info.get("is_read", False)
    msg_type = chat_info.get("msg_type", "text")
    
    task_file.write_text(
        f"""---
type: whatsapp_message
source: whatsapp_cloud_api
from_name: {sender_name}
from_number: {wa_id}
received: {timestamp}
priority: {priority}
status: pending
chat_type: {"group" if is_group else "private"}
read_status: {"read" if is_read else "unread"}
message_type: {msg_type}
---

## WhatsApp Message {'📨' if is_group else '💬'}

**From:** {sender_name} (`{wa_id}`)
**Received:** {timestamp}
**Chat Type:** {"👥 Group" if is_group else "👤 Private"}
**Read Status:** {"✅ Read" if is_read else "🔵 Unread"}
**Message Type:** {msg_type.title()}

**Message:**
> {text}

## Detected Intent
{"⚠️ URGENT — contains urgent keyword" if priority == "high" else "Normal priority — standard review"}

## Chat Information
- **Group Chat:** {"Yes" if is_group else "No"}
- **Read Status:** {"Read" if is_read else "Unread"}
- **Message ID:** {chat_info.get("msg_id", "N/A")}

## Suggested Actions
- [ ] Read full conversation in WhatsApp
- [ ] Draft reply (requires approval — Handbook §3)
- [ ] Forward to relevant team member if needed
- [ ] Archive after responding

## Notes
_Add context or decision here._

---
*Privacy note: Message stored per Company Handbook §6*
""",
        encoding="utf-8",
    )

    return task_file


def _log_call_event(from_wa_id: str, call_type: str, duration: int, timestamp: str):
    """Log a call event to a separate file."""
    call_log_file = VAULT_PATH / "WhatsApp_Call_Log.md"
    
    call_entry = f"""
## {call_type} Call - {datetime.fromtimestamp(int(timestamp), tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}

- **From:** {from_wa_id}
- **Type:** {call_type}
- **Duration:** {duration} seconds
- **Status:** {"✅ Answered" if duration > 0 else "❌ Missed"}

---
"""
    
    if call_log_file.exists():
        content = call_log_file.read_text(encoding="utf-8")
        # Insert new entry after the header
        if "---" in content:
            parts = content.split("---", 1)
            content = parts[0] + "---\n" + call_entry + parts[1]
        else:
            content = call_entry + content
    else:
        content = f"""# WhatsApp Call Log

{call_entry}
"""
    
    call_log_file.write_text(content, encoding="utf-8")
    sys.stderr.write(f"[Webhook] Call logged: {call_type} from {from_wa_id} ({duration}s)\n")


def _send_auto_reply_sync(wa_id: str, message_text: str = ""):
    """Send an intelligent auto-reply via Meta Cloud API."""
    if not AUTO_REPLY_ENABLED or not wa_id:
        return None

    # Use dynamic token and phone number ID loaders
    access_token = _get_current_access_token()
    phone_number_id = _get_current_phone_number_id()
    if not access_token or not phone_number_id:
        sys.stderr.write("[Webhook] Auto-reply skipped: credentials not configured\n")
        return None

    # Generate intelligent response based on message content
    reply_text = _generate_intelligent_reply(message_text)

    try:
        import httpx

        url = f"https://graph.facebook.com/v25.0/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": wa_id,
            "type": "text",
            "text": {"body": reply_text},
        }

        with httpx.Client() as client:
            r = client.post(url, json=payload, headers=headers, timeout=15)
            result = r.json()
            if r.status_code == 200:
                sys.stderr.write(f"[Webhook] Auto-reply sent to {wa_id}\n")
            else:
                sys.stderr.write(f"[Webhook] Auto-reply failed ({r.status_code}): {result}\n")
            return result

    except Exception as e:
        sys.stderr.write(f"[Webhook] Auto-reply failed: {e}\n")
        return None


def _generate_intelligent_reply(message_text: str) -> str:
    """Generate an intelligent reply based on the message content."""
    if not message_text:
        return "Thanks for your message! 🤖 AI Employee here. How can I assist you today?"
    
    text_lower = message_text.lower()
    
    # Greeting responses
    greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "assalamualaikum", "salam"]
    if any(g in text_lower for g in greetings):
        return "Waalaikumussalam! 👋 Hello! I'm your AI Employee. How can I help you today? I can assist with emails, scheduling, tasks, and more!"
    
    # Farewell responses
    farewells = ["bye", "goodbye", "see you", "thank you", "thanks", "shukriya"]
    if any(f in text_lower for f in farewells):
        return "You're welcome! 😊 Feel free to reach out anytime. Have a great day!"
    
    # Question responses
    if "?" in message_text or "how" in text_lower or "what" in text_lower or "when" in text_lower or "where" in text_lower or "who" in text_lower or "why" in text_lower:
        return f"Great question! 🤔 I've received your message: \"{message_text[:100]}\". Let me process this and get back to you with a detailed response shortly. Is there anything else I can help you with?"
    
    # Urgent/Priority keywords
    urgent_keywords = ["urgent", "asap", "emergency", "immediately", "important", "priority"]
    if any(u in text_lower for u in urgent_keywords):
        return "⚠️ URGENT MESSAGE RECEIVED ⚠️\n\nI've flagged your message as high priority and will escalate it immediately. Someone will respond to you within 15 minutes. Thank you for your patience!"
    
    # Meeting/Scheduling requests
    if any(word in text_lower for word in ["meeting", "schedule", "appointment", "call", "zoom", "teams"]):
        return "📅 I can help you schedule that! Please provide:\n- Date & Time\n- Duration\n- Attendees\n- Meeting link (if any)\n\nI'll create a calendar event and send invitations."
    
    # Invoice/Payment queries
    if any(word in text_lower for word in ["invoice", "payment", "bill", "pay", "money", "price", "cost"]):
        return "💰 Regarding your payment inquiry: I'll forward this to our accounts team. They'll respond with the details within 24 hours. Reference number will be created in your task file."
    
    # Technical support
    if any(word in text_lower for word in ["help", "support", "issue", "problem", "error", "bug", "not working"]):
        return "🔧 I'm here to help! I've created a support ticket for your issue. Our technical team will review and respond within 4 hours. Please share any screenshots or error messages if available."
    
    # Order/Product inquiries
    if any(word in text_lower for word in ["order", "product", "buy", "purchase", "price", "available", "stock"]):
        return "📦 Thanks for your interest! I'll connect you with our sales team who can provide detailed product information and pricing. Expected response time: 2-4 hours."
    
    # Default response for other messages
    return f"Thanks for your message! 🤖 AI Employee here.\n\nI received: \"{message_text[:50]}{'...' if len(message_text) > 50 else ''}\"\n\nI'm processing your request and will respond properly shortly. How else can I assist you today?"


async def _send_auto_reply(wa_id: str):
    """Async wrapper for auto-reply (kept for compatibility)."""
    return _send_auto_reply_sync(wa_id)


# ── Flask Webhook Server ──────────────────────────────────────────────────────

def create_app():
    """Create Flask app for webhook server."""
    try:
        from flask import Flask, request, jsonify
    except ImportError:
        sys.stderr.write("ERROR: Flask not installed. Run: uv add flask\n")
        raise SystemExit(1)

    app = Flask(__name__)

    @app.route("/webhook", methods=["GET"])
    def verify_webhook():
        """Meta verifies the webhook during setup."""
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        # Use dynamic verify token loader
        verify_token = _get_env_from_file("WHATSAPP_VERIFY_TOKEN", "")

        if mode == "subscribe" and token == verify_token:
            sys.stderr.write("[Webhook] Verification successful\n")
            return challenge, 200

        sys.stderr.write(f"[Webhook] Verification failed: mode={mode}, token={token}\n")
        return jsonify({"error": "Verification failed"}), 403

    @app.route("/webhook", methods=["POST"])
    def handle_webhook():
        """Receive inbound WhatsApp messages from Meta."""
        
        # Check lockdown mode
        lockdown_file = VAULT_PATH / ".lockdown_mode"
        if lockdown_file.exists():
            sys.stderr.write("[Webhook] LOCKDOWN MODE ACTIVE - Message blocked\n")
            return jsonify({"status": "blocked", "reason": "lockdown_mode"}), 200
        
        data = request.get_json()
        sys.stderr.write(f"[Webhook] Received: {json.dumps(data, indent=2)[:500]}\n")

        if not data or "entry" not in data:
            return jsonify({"status": "ok"}), 200

        # Process each entry
        for entry in data["entry"]:
            # Get phone number ID for this webhook
            webhook_phone_number_id = entry.get("id")

            # Process messages from each change
            for change in entry.get("changes", []):
                if change.get("field") != "messages":
                    continue
                
                # Get messaging product from value (Meta's actual structure)
                value = change.get("value", {})
                messaging_product = value.get("messaging_product", "whatsapp")
                if messaging_product != "whatsapp":
                    continue

                messages = value.get("messages", [])
                contacts = value.get("contacts", [])

                # Build contact lookup
                contact_map = {c.get("wa_id"): c.get("profile", {}).get("name", "Unknown")
                               for c in contacts if c.get("wa_id")}

                for msg in messages:
                    msg_id = msg.get("id")
                    msg_type = msg.get("type")
                    timestamp = msg.get("timestamp")

                    # Skip if already processed
                    if msg_id in _seen_message_ids:
                        sys.stderr.write(f"[Webhook] Duplicate message {msg_id}, skipping\n")
                        continue

                    from_wa_id = msg.get("from")
                    
                    # Extract chat information
                    chat_info = {
                        "msg_id": msg_id,
                        "msg_type": msg_type,
                        "from": from_wa_id,
                        "timestamp": timestamp,
                        "is_group": False,
                        "is_read": False,
                        "call_status": None,
                    }

                    # Check if it's a group message
                    if msg.get("context"):
                        chat_info["is_group"] = msg["context"].get("from", "") != from_wa_id
                        chat_info["group_id"] = msg["context"].get("id", "")
                    
                    # Check read status from metadata
                    if msg.get("status"):
                        chat_info["is_read"] = msg["status"] == "read"

                    # Process based on message type
                    if msg_type == "text":
                        text_body = msg.get("text", {}).get("body", "")
                        sender_name = contact_map.get(from_wa_id, from_wa_id or "Unknown")
                        
                        # Create task file
                        message_data = {
                            "sender_name": sender_name,
                            "text": text_body[:500],
                            "timestamp": datetime.fromtimestamp(
                                int(timestamp), tz=timezone.utc
                            ).isoformat() if timestamp else datetime.now(timezone.utc).isoformat(),
                            "wa_id": from_wa_id,
                            "message_id": msg_id,
                            "chat_info": chat_info,
                        }

                        try:
                            task_file = _create_task_file(message_data)
                            sys.stderr.write(
                                f"[Webhook] Task created: {task_file.name} "
                                f"(from: {sender_name}, priority: {_detect_priority(text_body)}, "
                                f"group: {chat_info['is_group']}, read: {chat_info['is_read']})\n"
                            )

                            # Mark as seen
                            _seen_message_ids.add(msg_id)
                            _save_seen()

                            # Send intelligent auto-reply (in background thread)
                            if AUTO_REPLY_ENABLED:
                                import threading
                                thread = threading.Thread(
                                    target=_send_auto_reply_sync,
                                    args=(from_wa_id, text_body),
                                    daemon=True
                                )
                                thread.start()

                        except Exception as e:
                            sys.stderr.write(f"[Webhook] Error creating task file: {e}\n")
                    
                    # Process call events
                    elif msg_type == "voice" or msg_type == "video":
                        call_duration = msg.get(msg_type, {}).get("duration_seconds", 0)
                        call_type = "Voice" if msg_type == "voice" else "Video"
                        sys.stderr.write(
                            f"[Webhook] {call_type} call received from {from_wa_id} "
                            f"(Duration: {call_duration}s)\n"
                        )
                        # Log call event
                        _log_call_event(from_wa_id, call_type, call_duration, timestamp)
                    
                    # Process status updates (read receipts)
                    elif msg_type == "reaction":
                        emoji = msg.get("reaction", {}).get("emoji", "")
                        sys.stderr.write(f"[Webhook] Reaction received: {emoji}\n")

        return jsonify({"status": "ok"}), 200

    @app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint for monitoring."""
        return jsonify({
            "status": "healthy",
            "webhook_port": WEBHOOK_PORT,
            "credentials_configured": bool(VERIFY_TOKEN and ACCESS_TOKEN and PHONE_NUMBER_ID),
            "auto_reply_enabled": AUTO_REPLY_ENABLED,
            "messages_processed": len(_seen_message_ids),
        }), 200

    @app.route("/test-send", methods=["POST"])
    def test_send():
        """Test sending a WhatsApp message via Cloud API."""
        # Restrict to localhost only for security
        if request.remote_addr not in ("127.0.0.1", "::1", "localhost"):
            return jsonify({"error": "Forbidden - localhost only"}), 403
        
        data = request.get_json() or {}
        to = data.get("to", "")
        message = data.get("message", "Test message from AI Employee")

        if not to:
            return jsonify({"error": "Missing 'to' phone number"}), 400

        # Use dynamic token and phone number ID loaders
        access_token = _get_current_access_token()
        phone_number_id = _get_current_phone_number_id()
        if not access_token or not phone_number_id:
            return jsonify({"error": "Credentials not configured"}), 500

        try:
            import httpx

            url = f"https://graph.facebook.com/v25.0/{phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": message},
            }

            with httpx.Client() as client:
                r = client.post(url, json=payload, headers=headers, timeout=15)
                result = r.json()

                if r.status_code == 200:
                    return jsonify({"success": True, "result": result}), 200
                else:
                    return jsonify({"success": False, "error": result}), r.status_code

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/stats", methods=["GET"])
    def stats():
        """Return webhook statistics."""
        received_count = len(list(NEEDS_ACTION.glob("WHATSAPP_*.md"))) if NEEDS_ACTION.exists() else 0
        return jsonify({
            "messages_received_total": received_count,
            "messages_processed_session": len(_seen_message_ids),
            "webhook_port": WEBHOOK_PORT,
            "uptime": "running",
        }), 200

    return app


# ── Self-Test ─────────────────────────────────────────────────────────────────

def _run_self_test():
    """Test webhook connectivity after startup."""
    import urllib.request
    import urllib.error

    print("\n=== WhatsApp Webhook Self-Test ===\n")

    # Test health endpoint
    try:
        with urllib.request.urlopen(f"http://localhost:{WEBHOOK_PORT}/health", timeout=5) as r:
            data = json.loads(r.read().decode())
            print(f"✓ Health check: {data['status']}")
            print(f"  - Credentials configured: {data['credentials_configured']}")
            print(f"  - Auto-reply enabled: {data['auto_reply_enabled']}")
    except Exception as e:
        print(f"✗ Health check failed: {e}")

    # Test stats endpoint
    try:
        with urllib.request.urlopen(f"http://localhost:{WEBHOOK_PORT}/stats", timeout=5) as r:
            data = json.loads(r.read().decode())
            print(f"✓ Stats: {data['messages_received_total']} messages received")
    except Exception as e:
        print(f"✗ Stats check failed: {e}")

    print("\n=== Test Complete ===\n")


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="WhatsApp Cloud API Webhook Server")
    parser.add_argument("--vault", type=str, default=None,
                        help="Vault path (used by orchestrator)")
    parser.add_argument("--port", type=int, default=WEBHOOK_PORT,
                        help=f"Webhook port (default: {WEBHOOK_PORT})")
    parser.add_argument("--test", action="store_true",
                        help="Run self-test after startup")
    args = parser.parse_args()

    # Load seen messages
    _load_seen()

    # Validate configuration
    if not VERIFY_TOKEN:
        sys.stderr.write("WARNING: WHATSAPP_VERIFY_TOKEN not set — webhook verification will fail\n")
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
        sys.stderr.write("WARNING: WhatsApp credentials incomplete — sending will fail\n")

    print(f"\n=== WhatsApp Webhook Server ===")
    print(f"Port: {args.port}")
    print(f"Verify Token: {'configured' if VERIFY_TOKEN else 'NOT SET'}")
    print(f"Access Token: {'configured' if ACCESS_TOKEN else 'NOT SET'}")
    print(f"Phone Number ID: {'configured' if PHONE_NUMBER_ID else 'NOT SET'}")
    print(f"Auto-Reply: {'enabled' if AUTO_REPLY_ENABLED else 'disabled'}")
    print(f"\nWebhook URL for Meta: https://your-domain.com/webhook")
    print(f"Health check: http://localhost:{args.port}/health")
    print(f"\nStarting Flask server... Press Ctrl+C to stop.\n")

    # Create and run app
    app = create_app()

    if args.test:
        # Start server in background, then run test
        import threading
        import time

        def run_server():
            app.run(host="0.0.0.0", port=args.port, debug=False, use_reloader=False)

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        time.sleep(2)  # Wait for server to start
        _run_self_test()

        # Keep running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
    else:
        app.run(host="0.0.0.0", port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
