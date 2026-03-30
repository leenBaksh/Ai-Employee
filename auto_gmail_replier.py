"""
auto_gmail_replier.py - Full Gmail Automation with Auto-Reply

This script:
1. Checks Gmail for new important emails
2. Analyzes email content and priority
3. Generates intelligent auto-replies
4. Sends replies via SMTP
5. Creates task files and logs everything

Usage:
    uv run python auto_gmail_replier.py
"""

import os
import json
import smtplib
from pathlib import Path
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()
NEEDS_ACTION = VAULT_PATH / "Needs_Action"
DONE_DIR = VAULT_PATH / "Done"
LOGS_DIR = VAULT_PATH / "Logs"

# SMTP Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "AI Employee")

# Auto-Reply Configuration
AUTO_REPLY_ENABLED = os.getenv("GMAIL_AUTO_REPLY", "false").lower() == "true"
AUTO_REPLY_SIGNATURE = "\n\n--\nAI Employee | Automated Response\nwdigital085@gmail.com"

# Ensure directories exist
NEEDS_ACTION.mkdir(parents=True, exist_ok=True)
DONE_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def analyze_email_priority(subject: str, snippet: str) -> str:
    """Analyze email priority based on content."""
    
    urgent_keywords = [
        "urgent", "asap", "emergency", "immediately", "critical",
        "invoice", "payment", "overdue", "deadline", "action required"
    ]
    
    high_keywords = [
        "important", "priority", "review", "approval", "decision",
        "meeting", "schedule", "call", "interview"
    ]
    
    text = (subject + " " + snippet).lower()
    
    if any(kw in text for kw in urgent_keywords):
        return "high"
    elif any(kw in text for kw in high_keywords):
        return "normal"
    else:
        return "low"


def generate_auto_reply(subject: str, snippet: str, from_email: str) -> str:
    """Generate intelligent auto-reply based on email content."""
    
    priority = analyze_email_priority(subject, snippet)
    text = (subject + " " + snippet).lower()
    
    # Greeting
    if "hello" in text or "hi" in text:
        greeting = "Hello,"
    elif "dear" in text:
        greeting = "Dear Colleague,"
    else:
        greeting = "Hi there,"
    
    # Generate response based on content
    if any(kw in text for kw in ["invoice", "payment", "bill"]):
        body = f"""{greeting}

Thank you for your email regarding payment/invoice matters.

I've received your message and logged it in our system. Our finance team will review and respond within 24 hours.

Reference: {datetime.now().strftime('%Y%m%d-%H%M')}

Best regards,
AI Employee"""

    elif any(kw in text for kw in ["meeting", "schedule", "appointment", "call"]):
        body = f"""{greeting}

Thank you for reaching out about scheduling a meeting.

I've received your request and will coordinate with the relevant team members. You'll receive a calendar invitation or confirmation within 24 hours.

Reference: {datetime.now().strftime('%Y%m%d-%H%M')}

Best regards,
AI Employee"""

    elif any(kw in text for kw in ["job", "career", "position", "application", "resume"]):
        body = f"""{greeting}

Thank you for your interest in career opportunities.

I've received your application/inquiry and forwarded it to our HR team. They will review and get back to you within 5-7 business days.

Reference: {datetime.now().strftime('%Y%m%d-%H%M')}

Best regards,
AI Employee"""

    elif any(kw in text for kw in ["support", "help", "issue", "problem", "error"]):
        body = f"""{greeting}

Thank you for contacting support.

I've received your request and created a support ticket. Our technical team will investigate and respond within 24 hours.

Reference: {datetime.now().strftime('%Y%m%d-%H%M')}

Best regards,
AI Employee"""

    elif priority == "high":
        body = f"""{greeting}

Thank you for your urgent message.

I've flagged this as high priority and escalated it to the relevant team. You'll receive a response within 4 hours.

Reference: {datetime.now().strftime('%Y%m%d-%H%M')}

Best regards,
AI Employee"""

    else:
        body = f"""{greeting}

Thank you for your email.

I've received your message and logged it in our system. We'll review and respond within 24-48 hours.

Reference: {datetime.now().strftime('%Y%m%d-%H%M')}

Best regards,
AI Employee"""

    return body + AUTO_REPLY_SIGNATURE


def send_email_reply(to_email: str, subject: str, body: str, in_reply_to: str = None):
    """Send email reply via SMTP."""
    
    if not SMTP_USER or not SMTP_PASSWORD:
        print("   ⚠️  SMTP not configured")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"{SMTP_FROM_NAME} <{SMTP_USER}>"
        msg['To'] = to_email
        msg['Subject'] = "Re: " + subject
        
        if in_reply_to:
            msg['In-Reply-To'] = in_reply_to
            msg['References'] = in_reply_to
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Connect and send
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print("   ✅ Reply sent via SMTP")
        return True
        
    except Exception as e:
        print(f"   ⚠️  Send error: {e}")
        return False


def process_gmail_auto_reply():
    """Main function to process Gmail and send auto-replies."""
    
    print("=" * 50)
    print("  📧 Gmail Full Automation")
    print("=" * 50)
    print()
    
    # Check configuration
    print("📋 Configuration Check:")
    print(f"   SMTP User: {SMTP_USER or 'Not configured'}")
    print(f"   Auto-Reply: {'Enabled' if AUTO_REPLY_ENABLED else 'Disabled'}")
    print()
    
    # Check for new emails in Needs_Action
    print("📥 Checking for new emails...")
    
    today = datetime.now(timezone.utc)
    today_slug = today.strftime("%Y%m%d")
    
    emails_processed = 0
    replies_sent = 0
    
    if NEEDS_ACTION.exists():
        email_files = list(NEEDS_ACTION.glob(f"EMAIL_{today_slug}*.md"))
        
        for email_file in email_files:
            content = email_file.read_text(encoding='utf-8')
            
            # Parse email metadata
            lines = content.splitlines()
            email_data = {}
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    email_data[key.strip().lower()] = value.strip()
            
            # Check if already replied
            if 'replied: true' in content.lower():
                continue
            
            emails_processed += 1
            
            from_email = email_data.get('from', '')
            subject = email_data.get('subject', email_file.stem)
            snippet = email_data.get('snippet', '')
            
            print(f"\n📧 Processing: {subject}")
            print(f"   From: {from_email}")
            
            # Analyze priority
            priority = analyze_email_priority(subject, snippet)
            print(f"   Priority: {priority}")
            
            # Generate and send auto-reply
            if AUTO_REPLY_ENABLED and from_email and '@' in from_email:
                print("   📝 Generating auto-reply...")
                reply_body = generate_auto_reply(subject, snippet, from_email)
                
                if send_email_reply(from_email, subject, reply_body):
                    replies_sent += 1
                    
                    # Mark as replied
                    updated_content = content.replace(
                        'status: pending',
                        'status: pending\nreplied: true\nreply_sent: ' + datetime.now(timezone.utc).isoformat()
                    )
                    email_file.write_text(updated_content, encoding='utf-8')
                    
                    # Move to Done
                    done_file = DONE_DIR / email_file.name
                    done_file.write_text(updated_content, encoding='utf-8')
                    print("   ✅ Processed and archived")
    
    print()
    print("=" * 50)
    print("  ✅ Gmail Automation Complete!")
    print("=" * 50)
    print()
    print(f"📊 Summary:")
    print(f"   Emails Processed: {emails_processed}")
    print(f"   Auto-Replies Sent: {replies_sent}")
    print(f"   Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print()
    
    # Log activity
    log_file = LOGS_DIR / f"{today.strftime('%Y-%m-%d')}.json"
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "gmail_auto_reply",
        "emails_processed": emails_processed,
        "replies_sent": replies_sent
    }
    
    if log_file.exists():
        try:
            logs = json.loads(log_file.read_text())
            logs.append(log_entry)
            log_file.write_text(json.dumps(logs, indent=2))
        except:
            log_file.write_text(json.dumps([log_entry], indent=2))
    else:
        log_file.write_text(json.dumps([log_entry], indent=2))
    
    return emails_processed, replies_sent


if __name__ == "__main__":
    process_gmail_auto_reply()
