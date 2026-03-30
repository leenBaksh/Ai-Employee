#!/usr/bin/env python3
"""
WhatsApp Reply Script - Send replies to specific phone numbers

Usage:
    uv run python scripts/whatsapp_reply.py +923103871019 "Your reply message here"
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv(Path(__file__).parent.parent / ".env")

ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

def send_whatsapp_reply(to: str, message: str):
    """Send a WhatsApp reply to a phone number."""
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
        print("❌ Error: WhatsApp credentials not configured")
        print("   Set WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID in .env")
        return False
    
    # Clean phone number (remove +, spaces, dashes)
    to = to.replace("+", "").replace(" ", "").replace("-", "")
    
    import httpx
    
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }
    
    try:
        with httpx.Client() as client:
            r = client.post(url, json=payload, headers=headers, timeout=15)
            result = r.json()
            
            if r.status_code == 200:
                msg_id = result.get("messages", [{}])[0].get("id", "N/A")
                print(f"✅ Message sent successfully!")
                print(f"   To: +{to}")
                print(f"   Message ID: {msg_id}")
                return True
            else:
                print(f"❌ Failed to send message ({r.status_code})")
                print(f"   Error: {result}")
                return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("📱 WhatsApp Reply Tool")
        print("=" * 40)
        print(f"\nUsage: uv run python {sys.argv[0]} <phone> <message>\n")
        print("Examples:")
        print('  uv run python scripts/whatsapp_reply.py +923103871019 "Hello!"')
        print('  uv run python scripts/whatsapp_reply.py 923103871019 "Thanks for your message"')
        print("\nCurrent Config:")
        print(f"  Token: {'✅ Configured' if ACCESS_TOKEN else '❌ Missing'}")
        print(f"  Phone ID: {'✅ Configured' if PHONE_NUMBER_ID else '❌ Missing'}")
        sys.exit(1)
    
    phone = sys.argv[1]
    message = " ".join(sys.argv[2:])
    
    print(f"📱 Sending WhatsApp reply...")
    print(f"   To: {phone}")
    print(f"   Message: {message[:50]}...")
    print()
    
    success = send_whatsapp_reply(phone, message)
    sys.exit(0 if success else 1)
