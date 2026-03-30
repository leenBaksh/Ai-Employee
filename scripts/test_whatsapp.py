#!/usr/bin/env python3
"""
test_whatsapp.py — End-to-end WhatsApp integration test.

Tests:
  1. Cloud API credentials (send test message)
  2. Webhook server (start and verify health)
  3. WhatsApp Web session (if available)
  4. Task file creation (simulate incoming message)

Usage:
    uv run python scripts/test_whatsapp.py
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

# Colors
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✓{RESET} {msg}")

def print_warning(msg):
    print(f"{YELLOW}⚠{RESET} {msg}")

def print_error(msg):
    print(f"{RED}✗{RESET} {msg}")

def print_header(msg):
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}{msg:^60}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")


def test_cloud_api_credentials():
    """Test sending a message via Cloud API."""
    print_header("Test 1: Cloud API Credentials")
    
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    
    if not access_token or not phone_number_id:
        print_warning("Credentials not configured — skipping Cloud API test")
        return None
    
    try:
        import httpx
        
        # Test 1: Verify phone number
        url = f"https://graph.facebook.com/v25.0/{phone_number_id}"
        params = {
            "fields": "display_phone_number,quality_rating",
            "access_token": access_token
        }
        
        print("Testing phone number configuration...")
        with httpx.Client() as client:
            r = client.get(url, params=params, timeout=15)
            
            if r.status_code == 200:
                data = r.json()
                print_success(f"Phone number verified: {data.get('display_phone_number', 'N/A')}")
                print_success(f"Quality rating: {data.get('quality_rating', 'N/A')}")
            else:
                print_error(f"API request failed: {r.status_code}")
                print_error(f"Response: {r.text[:200]}")
                return False
        
        # Test 2: Send test message (if test number provided)
        test_number = os.getenv("WHATSAPP_TEST_NUMBER", "")
        if test_number:
            print(f"\nSending test message to {test_number}...")
            
            url = f"https://graph.facebook.com/v25.0/{phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": test_number,
                "type": "text",
                "text": {
                    "body": f"🤖 AI Employee Test Message\n\nTimestamp: {datetime.now().isoformat()}\n\nIf you receive this, the Cloud API integration is working correctly!"
                },
            }
            
            with httpx.Client() as client:
                r = client.post(url, json=payload, headers=headers, timeout=15)
                result = r.json()
                
                if r.status_code == 200 and result.get("messages"):
                    print_success(f"Test message sent! ID: {result['messages'][0]['id']}")
                    return True
                else:
                    print_error(f"Message send failed: {result}")
                    return False
        else:
            print_warning("\nSet WHATSAPP_TEST_NUMBER in .env to send test message")
            print_info("Skipping send test — credentials are valid")
            return True
            
    except httpx.ConnectError as e:
        print_error(f"Network error: {e}")
        return False
    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def test_webhook_server():
    """Start webhook server and test health endpoint."""
    print_header("Test 2: Webhook Server")
    
    webhook_port = int(os.getenv("WHATSAPP_WEBHOOK_PORT", "8089"))
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    
    print(f"Starting webhook server on port {webhook_port}...")
    
    # Import and start server in background
    sys.path.insert(0, str(PROJECT_ROOT / "watchers"))
    from whatsapp_webhook_server import _load_seen, create_app
    import threading
    
    _load_seen()
    app = create_app()
    
    def run_server():
        app.run(host="0.0.0.0", port=webhook_port, debug=False, use_reloader=False)
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    time.sleep(2)  # Wait for server to start
    
    # Test health endpoint
    try:
        with urllib.request.urlopen(f"http://localhost:{webhook_port}/health", timeout=5) as r:
            data = json.loads(r.read().decode())
            
            if data.get("status") == "healthy":
                print_success(f"Health check: {data['status']}")
                print_success(f"Credentials configured: {data['credentials_configured']}")
                print_success(f"Auto-reply enabled: {data['auto_reply_enabled']}")
            else:
                print_error(f"Health check returned: {data}")
                return False
    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False
    
    # Test webhook verification endpoint
    try:
        test_url = f"http://localhost:{webhook_port}/webhook?hub.mode=subscribe&hub.verify_token={verify_token}&hub.challenge=12345"
        with urllib.request.urlopen(test_url, timeout=5) as r:
            challenge = r.read().decode()
            if challenge == "12345":
                print_success("Webhook verification test passed")
            else:
                print_error(f"Webhook verification returned wrong challenge: {challenge}")
                return False
    except Exception as e:
        print_error(f"Webhook verification test failed: {e}")
        return False
    
    # Test stats endpoint
    try:
        with urllib.request.urlopen(f"http://localhost:{webhook_port}/stats", timeout=5) as r:
            data = json.loads(r.read().decode())
            print_success(f"Stats endpoint: {data['messages_received_total']} messages received")
    except Exception as e:
        print_error(f"Stats endpoint failed: {e}")
    
    print_success("Webhook server is running and healthy")
    print_info(f"Webhook URL: http://localhost:{webhook_port}/webhook")
    print_info("Press Ctrl+C to stop the server")
    
    return True


def test_whatsapp_web_session():
    """Test WhatsApp Web browser session."""
    print_header("Test 3: WhatsApp Web Session")
    
    session_path = Path(os.getenv("WHATSAPP_SESSION_PATH", "./secrets/whatsapp_session")).resolve()
    
    if not session_path.exists():
        print_warning("Session directory not found")
        print_info("Run: uv run whatsapp-watcher --setup")
        return False
    
    print_success(f"Session directory exists: {session_path}")
    
    # Check for browser profile
    default_dir = session_path / "Default"
    if not default_dir.exists():
        print_warning("Browser profile missing")
        print_info("Run: uv run whatsapp-watcher --setup")
        return False
    
    print_success("Browser profile found")

    # Try to verify with Playwright
    try:
        from playwright.sync_api import sync_playwright

        print("Testing session with Playwright...")

        playwright = None
        browser = None
        try:
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch_persistent_context(
                str(session_path),
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )

            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto("https://web.whatsapp.com", wait_until="domcontentloaded", timeout=20000)

            # Check if logged in
            try:
                page.wait_for_selector('[data-testid="chat-list"]', timeout=5000)
                print_success("WhatsApp Web session is valid and logged in")
                return True
            except Exception:
                print_warning("Session may be expired (QR code visible)")
                return False
        finally:
            try:
                if browser:
                    browser.close()
            except Exception:
                pass
            try:
                if playwright:
                    playwright.stop()
            except Exception:
                pass

    except ImportError:
        print_warning("Playwright not installed")
        print_info("Run: uv add playwright && playwright install chromium")
        return False
    except Exception as e:
        print_error(f"Session test failed: {e}")
        return False


def test_task_file_creation():
    """Test creating a WhatsApp task file."""
    print_header("Test 4: Task File Creation")
    
    vault_path = Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()
    needs_action = vault_path / "Needs_Action"
    needs_action.mkdir(parents=True, exist_ok=True)
    
    # Create test task file
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    task_file = needs_action / f"WHATSAPP_TEST_{ts}.md"
    
    content = f"""---
type: whatsapp_message
source: test
from_name: Test User
from_number: +1234567890
received: {datetime.now(timezone.utc).isoformat()}
priority: normal
status: pending
---

## WhatsApp Message (Test)

**From:** Test User
**Received:** {datetime.now(timezone.utc).isoformat()}

**Message:**
> This is a test message created by test_whatsapp.py

## Detected Intent
Test message — no action required

## Suggested Actions
- [ ] Verify file format
- [ ] Delete this test file
- [ ] Confirm integration working

---
*Test message*
"""
    
    try:
        task_file.write_text(content, encoding="utf-8")
        print_success(f"Task file created: {task_file.name}")
        print_info(f"Location: {task_file}")
        
        # Verify file can be read
        read_content = task_file.read_text(encoding="utf-8")
        if "Test User" in read_content:
            print_success("Task file content verified")
            return True
        else:
            print_error("Task file content mismatch")
            return False
            
    except Exception as e:
        print_error(f"Task file creation failed: {e}")
        return False


def main():
    print(f"\n{BOLD}WhatsApp Integration — End-to-End Test{RESET}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Project: {PROJECT_ROOT}\n")
    
    results = {
        "Cloud API": None,
        "Webhook Server": None,
        "WhatsApp Web Session": None,
        "Task File Creation": None,
    }
    
    # Run tests
    results["Cloud API"] = test_cloud_api_credentials()
    results["Webhook Server"] = test_webhook_server()
    results["WhatsApp Web Session"] = test_whatsapp_web_session()
    results["Task File Creation"] = test_task_file_creation()
    
    # Summary
    print_header("Test Summary")
    
    for test_name, result in results.items():
        if result is True:
            print_success(f"{test_name}: PASSED")
        elif result is False:
            print_error(f"{test_name}: FAILED")
        else:
            print_warning(f"{test_name}: SKIPPED")
    
    passed = sum(1 for r in results.values() if r is True)
    total = sum(1 for r in results.values() if r is not None)
    
    print(f"\n{BOLD}Results: {passed}/{total} tests passed{RESET}\n")
    
    if passed == total:
        print_success("All tests passed! WhatsApp integration is ready.")
    elif passed > 0:
        print_warning("Some tests failed. See above for details.")
    else:
        print_error("All tests failed. Check configuration and try again.")
    
    print(f"\n{GREEN}Test complete!{RESET}\n")
    
    # Keep webhook server running if test passed
    if results["Webhook Server"]:
        print("Webhook server is still running. Press Ctrl+C to stop.\n")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")


if __name__ == "__main__":
    main()
