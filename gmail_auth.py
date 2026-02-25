"""
gmail_auth.py — Two-step Gmail OAuth for WSL2.

Step 1 (get URL):   uv run python gmail_auth.py url
Step 2 (exchange):  uv run python gmail_auth.py exchange "http://localhost:8085/?code=..."
"""
import sys, json, base64
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]
CREDENTIALS = "./secrets/gmail_credentials.json"
TOKEN_OUT    = "./secrets/gmail_token.json"
REDIRECT_URI = "http://localhost"


def get_flow():
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS, SCOPES)
    flow.redirect_uri = REDIRECT_URI
    return flow


def cmd_url():
    import subprocess
    import webbrowser
    from google_auth_oauthlib.flow import InstalledAppFlow
    
    # Use the library's built-in flow with local server
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS, SCOPES)
    flow.redirect_uri = REDIRECT_URI
    
    print("\nOpening browser for Google authorization...")
    print("Log in and click Allow. The browser will redirect and complete automatically.\n")
    
    # This runs a local server to catch the OAuth callback
    creds = flow.run_local_server(host='localhost', port=8085, open_browser=True)
    
    # Save the token
    token_data = json.loads(creds.to_json())
    Path(TOKEN_OUT).write_text(json.dumps(token_data, indent=2))
    print(f"\nOK: Token saved to {TOKEN_OUT}")
    print(f"OK: Scopes: {creds.scopes}")
    
    # Quick test
    from googleapiclient.discovery import build
    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    print(f"OK: Authorized as: {profile['emailAddress']}")
    print("\nGmail setup complete!\n")


def cmd_exchange(redirect_url: str):
    qs = parse_qs(urlparse(redirect_url).query)
    code = qs.get("code", [None])[0]
    if not code:
        print("ERROR: No 'code' found in URL. Did you copy the right URL?")
        sys.exit(1)

    flow = get_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials

    token_data = json.loads(creds.to_json())
    Path(TOKEN_OUT).write_text(json.dumps(token_data, indent=2))
    print(f"Token saved to {TOKEN_OUT}")
    print(f"Scopes: {creds.scopes}")

    # Quick test: get Gmail profile
    from googleapiclient.discovery import build
    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    print(f"Authorized as: {profile['emailAddress']}")
    print("\nGmail credentials fixed! Re-run the orchestrator to start Gmail watcher.")


def cmd_send():
    """Send the pending invoice email using saved token."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(TOKEN_OUT, SCOPES)
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())

    service = build("gmail", "v1", credentials=creds)

    import os
    smtp_user = os.getenv("SMTP_USER", "")
    msg_text = f"""From: AI Employee <{smtp_user}>
To: client@example.com
Subject: Re: Send January Invoice - Invoice INV-2026-01-001
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

Hi,

Thank you for your patience - please find your invoice for January consulting services below.

Invoice Details:
- Invoice #: INV-2026-01-001
- Service: January consulting services
- Amount: $500.00 USD
- Invoice Date: 2026-01-31
- Due Date: 2026-02-28 (Net-30)

Please let me know if you have any questions or need any adjustments.

Best regards,
World Digital

---
*This email was drafted with AI assistance.*"""

    raw = base64.urlsafe_b64encode(msg_text.encode()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"Email sent! Message ID: {result['id']}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "url"
    if cmd == "url":
        cmd_url()
    elif cmd == "exchange":
        if len(sys.argv) < 3:
            print("Usage: uv run python gmail_auth.py exchange '<redirect_url>'")
            sys.exit(1)
        cmd_exchange(sys.argv[2])
    elif cmd == "send":
        cmd_send()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
