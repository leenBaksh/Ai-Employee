#!/usr/bin/env python3
"""
whatsapp_setup.py — Comprehensive WhatsApp setup and diagnostics for AI Employee.

This script:
  1. Checks Python dependencies (Playwright, Flask, httpx)
  2. Validates .env configuration
  3. Tests Meta Cloud API credentials
  4. Checks WhatsApp Web session
  5. Provides setup instructions for both methods
  6. Optionally starts the webhook server for testing

Usage:
    uv run python scripts/whatsapp_setup.py          # full diagnostics
    uv run python scripts/whatsapp_setup.py --setup-web  # WhatsApp Web QR login
    uv run python scripts/whatsapp_setup.py --test-webhook # test webhook server
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

# ── Colors for terminal output ────────────────────────────────────────────────

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓{Colors.RESET} {msg}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {msg}")

def print_error(msg):
    print(f"{Colors.RED}✗{Colors.RESET} {msg}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ{Colors.RESET} {msg}")

def print_header(msg):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{msg:^60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")


# ── Dependency Checks ─────────────────────────────────────────────────────────

def check_dependencies():
    """Check if required Python packages are installed."""
    print_header("1. Checking Dependencies")
    
    issues = []
    
    # Playwright
    try:
        from playwright.sync_api import sync_playwright
        print_success("Playwright is installed")
    except ImportError:
        print_error("Playwright NOT installed")
        issues.append("Playwright required for WhatsApp Web automation")
    
    # Flask
    try:
        import flask
        print_success(f"Flask is installed (v{flask.__version__})")
    except ImportError:
        print_error("Flask NOT installed")
        issues.append("Flask required for WhatsApp webhook server")
    
    # httpx
    try:
        import httpx
        print_success(f"httpx is installed (v{httpx.__version__})")
    except ImportError:
        print_error("httpx NOT installed")
        issues.append("httpx required for Cloud API calls")
    
    if issues:
        print_warning("\nMissing dependencies detected!")
        print_info("Fix: cd /mnt/d/Hackathon-00/Ai-Employee && uv sync")
        print_info("Then: playwright install chromium")
        return False
    
    print_success("All dependencies installed")
    return True


# ── Configuration Checks ──────────────────────────────────────────────────────

def check_configuration():
    """Validate .env configuration."""
    print_header("2. Checking Configuration (.env)")
    
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    webhook_port = os.getenv("WHATSAPP_WEBHOOK_PORT", "8089")
    auto_reply = os.getenv("WHATSAPP_AUTO_REPLY", "false").lower()
    session_path = os.getenv("WHATSAPP_SESSION_PATH", "./secrets/whatsapp_session")
    
    issues = []
    
    # Cloud API credentials
    if verify_token:
        print_success(f"WHATSAPP_VERIFY_TOKEN: configured ({verify_token[:20]}...)")
    else:
        print_error("WHATSAPP_VERIFY_TOKEN: NOT SET")
        issues.append("Required for Meta webhook verification")
    
    if access_token:
        token_prefix = access_token[:20] if len(access_token) > 20 else access_token
        print_success(f"WHATSAPP_ACCESS_TOKEN: configured ({token_prefix}...)")
        if not access_token.startswith("EAA"):
            print_warning("  Token doesn't start with 'EAA' - may be invalid")
    else:
        print_error("WHATSAPP_ACCESS_TOKEN: NOT SET")
        issues.append("Required for sending messages via Cloud API")
    
    if phone_number_id:
        print_success(f"WHATSAPP_PHONE_NUMBER_ID: {phone_number_id}")
    else:
        print_error("WHATSAPP_PHONE_NUMBER_ID: NOT SET")
        issues.append("Required for Cloud API")
    
    # Optional settings
    print_info(f"WHATSAPP_WEBHOOK_PORT: {webhook_port}")
    print_info(f"WHATSAPP_AUTO_REPLY: {auto_reply}")
    print_info(f"WHATSAPP_SESSION_PATH: {session_path}")
    
    if issues:
        print_warning(f"\n{len(issues)} configuration issue(s) found")
        print_info("Edit .env file to add missing values")
        print_info("See: https://developers.facebook.com/apps for Meta credentials")
        return False
    
    print_success("All required credentials configured")
    return True


# ── Cloud API Test ────────────────────────────────────────────────────────────

def test_cloud_api():
    """Test Meta Cloud API connectivity."""
    print_header("3. Testing Meta Cloud API")
    
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    
    if not access_token or not phone_number_id:
        print_warning("Skipping API test - credentials not configured")
        return False
    
    try:
        import httpx
        
        url = f"https://graph.facebook.com/v25.0/{phone_number_id}"
        params = {
            "fields": "display_phone_number,quality_rating",
            "access_token": access_token
        }
        
        with httpx.Client() as client:
            r = client.get(url, params=params, timeout=15)
            
            if r.status_code == 200:
                data = r.json()
                print_success("Cloud API connection successful!")
                print_info(f"  Phone Number: {data.get('display_phone_number', 'N/A')}")
                print_info(f"  Quality Rating: {data.get('quality_rating', 'N/A')}")
                print_info(f"  Phone Number ID: {data.get('id', 'N/A')}")
                return True
            elif r.status_code == 401:
                print_error("Authentication failed (401 Unauthorized)")
                print_info("  Access token may be expired or invalid")
                print_info("  Fix: Generate new token at https://developers.facebook.com/apps")
                return False
            elif r.status_code == 404:
                print_error(f"Phone Number ID not found: {phone_number_id}")
                return False
            else:
                print_error(f"API request failed: {r.status_code}")
                print_info(f"  Response: {r.text[:200]}")
                return False
                
    except httpx.ConnectError as e:
        print_error(f"Network error: {e}")
        print_info("  Check your internet connection")
        return False
    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


# ── WhatsApp Web Session Check ────────────────────────────────────────────────

def check_whatsapp_web_session():
    """Check WhatsApp Web browser session."""
    print_header("4. Checking WhatsApp Web Session")
    
    session_path = Path(os.getenv("WHATSAPP_SESSION_PATH", "./secrets/whatsapp_session")).resolve()
    
    if not session_path.exists():
        print_error(f"Session directory NOT found: {session_path}")
        print_info("Fix: uv run python scripts/whatsapp_setup.py --setup-web")
        return False
    
    print_success(f"Session directory exists: {session_path}")
    
    # Check for browser profile
    default_dir = session_path / "Default"
    if default_dir.exists():
        print_success("Browser profile found (Default/)")
    else:
        print_warning("Browser profile missing - session may be invalid")
        print_info("Fix: uv run python scripts/whatsapp_setup.py --setup-web")
        return False
    
    # Check for Local State file
    local_state = session_path / "Local State"
    if local_state.exists():
        print_success("Browser state file found")
    else:
        print_warning("Browser state file missing")
    
    # Try to verify Playwright can use the session
    try:
        from playwright.sync_api import sync_playwright

        print_info("Testing session with Playwright...")

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

            # Try to load WhatsApp Web
            page.goto("https://web.whatsapp.com", wait_until="domcontentloaded", timeout=20000)

            # Check if chat list is visible (logged in) or QR code (not logged in)
            try:
                page.wait_for_selector('[data-testid="chat-list"]', timeout=5000)
                print_success("WhatsApp Web session is VALID and logged in")
            except Exception:
                # Check for QR code
                try:
                    page.wait_for_selector('[data-testid="qr-code"]', timeout=2000)
                    print_warning("WhatsApp Web session EXPIRED - QR code visible")
                    if browser:
                        browser.close()
                    if playwright:
                        playwright.stop()
                    print_info("Fix: uv run python scripts/whatsapp_setup.py --setup-web")
                    return False
                except Exception:
                    print_warning("Could not determine session status")
                    if browser:
                        browser.close()
                    if playwright:
                        playwright.stop()
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

    except Exception as e:
        print_error(f"Session test failed: {e}")
        print_info("May need to re-login via --setup-web")
        return False


# ── Setup WhatsApp Web ────────────────────────────────────────────────────────

def setup_whatsapp_web():
    """Guide user through WhatsApp Web QR login."""
    print_header("WhatsApp Web Setup")
    
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print_error("Playwright not installed")
        print_info("Fix: uv add playwright && playwright install chromium")
        return False
    
    session_path = Path(os.getenv("WHATSAPP_SESSION_PATH", "./secrets/whatsapp_session")).resolve()
    session_path.mkdir(parents=True, exist_ok=True)
    
    print_info(f"Session will be saved to: {session_path}\n")
    print("A browser window will open.")
    print("Scan the QR code with your phone (WhatsApp → Linked Devices → Link a Device)")
    print("Once logged in, press Enter here to save the session.\n")
    
    input("Press Enter to continue...")

    playwright = None
    browser = None
    try:
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch_persistent_context(
            str(session_path),
            headless=False,
        )
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto("https://web.whatsapp.com")

        print("\nBrowser opened. Scan the QR code on your phone...")
        input("\nPress Enter after you are logged in to save the session: ")
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

    print_success("Session saved!")
    print("\nYou can now run the WhatsApp watcher:")
    print("  uv run whatsapp-watcher")
    print("\nOr start the full orchestrator:")
    print("  uv run orchestrator")
    
    return True


# ── Test Webhook Server ──────────────────────────────────────────────────────

def test_webhook_server():
    """Start webhook server and run self-test."""
    print_header("Testing WhatsApp Webhook Server")
    
    webhook_port = int(os.getenv("WHATSAPP_WEBHOOK_PORT", "8089"))
    
    print_info(f"Starting webhook server on port {webhook_port}...")
    print_info("Press Ctrl+C to stop the server\n")
    
    # Import and run the webhook server
    sys.path.insert(0, str(PROJECT_ROOT / "watchers"))
    from whatsapp_webhook_server import _load_seen, create_app
    
    _load_seen()
    
    app = create_app()
    
    # Run test in background
    import threading
    import time
    import urllib.request
    
    def run_server():
        app.run(host="0.0.0.0", port=webhook_port, debug=False, use_reloader=False)
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    time.sleep(2)  # Wait for server to start
    
    # Test health endpoint
    try:
        with urllib.request.urlopen(f"http://localhost:{webhook_port}/health", timeout=5) as r:
            data = json.loads(r.read().decode())
            print_success(f"Health check: {data['status']}")
            print_info(f"  Credentials: {'configured' if data['credentials_configured'] else 'NOT SET'}")
            print_info(f"  Auto-reply: {'enabled' if data['auto_reply_enabled'] else 'disabled'}")
    except Exception as e:
        print_error(f"Health check failed: {e}")
    
    print("\nWebhook server is running!")
    print(f"Webhook URL for Meta: https://your-domain.com/webhook")
    print(f"Health check: http://localhost:{webhook_port}/health")
    print(f"Stats: http://localhost:{webhook_port}/stats")
    print("\nFor local testing with ngrok:")
    print("  ngrok http 8089")
    print("  Then set webhook URL in Meta Developer Portal")
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down webhook server...")


# ── Summary & Recommendations ─────────────────────────────────────────────────

def print_summary(cloud_ok: bool, web_ok: bool):
    """Print summary and recommendations."""
    print_header("Summary & Recommendations")
    
    print("WhatsApp Integration Status:")
    print(f"  Meta Cloud API:  {'✅ Working' if cloud_ok else '❌ Issues detected'}")
    print(f"  WhatsApp Web:    {'✅ Working' if web_ok else '❌ Issues detected'}")
    
    print("\nRecommended Next Steps:")
    
    if cloud_ok:
        print("  ✓ Cloud API is ready for sending messages")
        print("  ✓ Set up webhook URL in Meta Developer Portal:")
        print("    1. Go to https://developers.facebook.com/apps")
        print("    2. Select your app → WhatsApp → Configuration")
        print("    3. Set Webhook URL: https://your-domain.com/webhook")
        print("    4. Set Verify Token: (from .env WHATSAPP_VERIFY_TOKEN)")
        print("  ✓ Start webhook server: uv run python watchers/whatsapp_webhook_server.py")
    else:
        print("  ⚠ Fix Cloud API issues before sending messages")
    
    if web_ok:
        print("  ✓ WhatsApp Web session is valid for receiving messages")
        print("  ✓ Start watcher: uv run whatsapp-watcher")
    else:
        print("  ⚠ Re-login to WhatsApp Web: uv run python scripts/whatsapp_setup.py --setup-web")
    
    print("\nArchitecture Options:")
    print("  Option A: Use Meta Cloud API (recommended for production)")
    print("            - Webhook server receives messages")
    print("            - Cloud API sends replies")
    print("            - No browser automation needed")
    print("\n  Option B: Use WhatsApp Web automation (for testing/local)")
    print("            - Browser polls WhatsApp Web")
    print("            - Creates task files in Needs_Action/")
    print("            - Requires periodic re-authentication")
    print("\n  Option C: Use both (hybrid approach)")
    print("            - Webhook for receiving (Cloud API)")
    print("            - WhatsApp Web as backup")
    print("            - Orchestrator can send via Cloud API")


# ── Main Entry Point ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="WhatsApp Setup & Diagnostics for AI Employee",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python scripts/whatsapp_setup.py           # Full diagnostics
  uv run python scripts/whatsapp_setup.py --setup-web  # WhatsApp Web QR login
  uv run python scripts/whatsapp_setup.py --test-webhook # Test webhook server
        """
    )
    
    parser.add_argument("--setup-web", action="store_true",
                        help="Run WhatsApp Web QR code login setup")
    parser.add_argument("--test-webhook", action="store_true",
                        help="Start and test webhook server")
    parser.add_argument("--skip-deps", action="store_true",
                        help="Skip dependency checks")
    
    args = parser.parse_args()
    
    print(f"\n{Colors.BOLD}WhatsApp Setup — AI Employee{Colors.RESET}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Project: {PROJECT_ROOT}\n")
    
    # Handle special modes
    if args.setup_web:
        setup_whatsapp_web()
        return
    
    if args.test_webhook:
        test_webhook_server()
        return
    
    # Full diagnostics
    cloud_ok = False
    web_ok = False
    
    if not args.skip_deps:
        deps_ok = check_dependencies()
        if not deps_ok:
            print_warning("\nSome dependencies missing. Continuing with diagnostics...")
    
    config_ok = check_configuration()
    
    if config_ok:
        cloud_ok = test_cloud_api()
    
    web_ok = check_whatsapp_web_session()
    
    print_summary(cloud_ok, web_ok)
    
    print(f"\n{Colors.GREEN}Setup complete!{Colors.RESET}\n")


if __name__ == "__main__":
    main()
