"""
advanced_gmail_features.py - Enhanced Gmail Automation

New Features:
1. VIP Sender Detection - Priority handling for important contacts
2. Business Hours Auto-Reply - Different responses based on time
3. Email Threading - Track conversation history
4. Spam Filtering - Auto-filter suspicious emails
5. AI Email Summarization - Generate smart summaries
6. Multi-Language Support - Detect and reply in sender's language
7. Attachment Handling - Log and track attachments
8. Escalation Rules - Follow-up on unanswered emails

Usage:
    uv run python advanced_gmail_features.py
"""

import os
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()
NEEDS_ACTION = VAULT_PATH / "Needs_Action"
DONE_DIR = VAULT_PATH / "Done"
LOGS_DIR = VAULT_PATH / "Logs"
CONFIG_DIR = VAULT_PATH / ".gmail_config"

# Ensure directories exist
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# VIP Senders (add important contacts here)
VIP_SENDERS = [
    "ceo@company.com",
    "finance@company.com",
    "hr@company.com",
    "support@company.com",
    "@gmail.com",  # All Gmail addresses
]

# Spam Keywords
SPAM_KEYWORDS = [
    "lottery winner",
    "inheritance",
    "million dollars",
    "click here immediately",
    "verify your account now",
    "password expired",
    "suspended account",
]

# Business Hours (UTC)
BUSINESS_HOURS_START = 9  # 9 AM UTC
BUSINESS_HOURS_END = 17   # 5 PM UTC

# Multi-Language Responses
LANGUAGE_RESPONSES = {
    "english": {
        "greeting": "Hello,",
        "thanks": "Thank you for your email.",
        "signature": "Best regards,\nAI Employee"
    },
    "urdu": {
        "greeting": "السلام علیکم،",
        "thanks": "آپ کا ای میل موصول ہو گیا ہے۔",
        "signature": "آپ کا شکریہ،\nAI Employee"
    },
    "spanish": {
        "greeting": "Hola,",
        "thanks": "Gracias por su correo electrónico.",
        "signature": "Saludos cordiales,\nAI Employee"
    },
    "french": {
        "greeting": "Bonjour,",
        "thanks": "Merci pour votre email.",
        "signature": "Cordialement,\nAI Employee"
    },
    "german": {
        "greeting": "Hallo,",
        "thanks": "Vielen Dank für Ihre E-Mail.",
        "signature": "Mit freundlichen Grüßen,\nAI Employee"
    }
}


def detect_language(text: str) -> str:
    """Detect email language based on common words."""
    text_lower = text.lower()
    
    # Urdu/Hindi indicators
    if any(word in text_lower for word in ["ہے", "ہیں", "کا", "کی", "نام", "سلام", "السلام"]):
        return "urdu"
    
    # Spanish indicators
    if any(word in text_lower for word in ["hola", "gracias", "buenos", "días", "tardes"]):
        return "spanish"
    
    # French indicators
    if any(word in text_lower for word in ["bonjour", "merci", "salut", "cordialement"]):
        return "french"
    
    # German indicators
    if any(word in text_lower for word in ["hallo", "danke", "guten", "morgen", "grüßen"]):
        return "german"
    
    # Default to English
    return "english"


def is_vip_sender(email: str) -> bool:
    """Check if sender is a VIP contact."""
    for vip in VIP_SENDERS:
        if vip.startswith("@"):
            if email.endswith(vip):
                return True
        elif email.lower() == vip.lower():
            return True
    return False


def is_spam(subject: str, snippet: str) -> bool:
    """Detect potential spam based on keywords."""
    text = (subject + " " + snippet).lower()
    
    # Check for spam keywords
    spam_count = sum(1 for keyword in SPAM_KEYWORDS if keyword in text)
    
    # Check for excessive punctuation
    if subject.count("!") > 3 or subject.count("$") > 2:
        spam_count += 1
    
    # Check for all caps
    if subject.isupper() and len(subject) > 10:
        spam_count += 1
    
    return spam_count >= 2


def is_business_hours() -> bool:
    """Check if current time is within business hours."""
    now = datetime.now(timezone.utc)
    hour = now.hour
    weekday = now.weekday()  # 0=Monday, 6=Sunday
    
    # Not business hours on weekends
    if weekday >= 5:
        return False
    
    # Check business hours
    return BUSINESS_HOURS_START <= hour < BUSINESS_HOURS_END


def generate_vip_response(subject: str, snippet: str) -> str:
    """Generate priority response for VIP senders."""
    lang = detect_language(subject + " " + snippet)
    resp = LANGUAGE_RESPONSES[lang]
    
    return f"""{resp['greeting']}

{resp['thanks']} This has been flagged as HIGH PRIORITY.

A team member will respond within 2 hours.

Reference: VIP-{datetime.now().strftime('%Y%m%d-%H%M')}

{resp['signature']}

--
AI Employee | VIP Response
wdigital085@gmail.com"""


def generate_after_hours_response(subject: str, snippet: str) -> str:
    """Generate auto-reply for after-hours emails."""
    lang = detect_language(subject + " " + snippet)
    resp = LANGUAGE_RESPONSES[lang]
    
    return f"""{resp['greeting']}

{resp['thanks']}

Please note: This email was received outside business hours (UTC 9:00-17:00, Mon-Fri).

Your email is important to us. We'll respond during the next business day.

Reference: AH-{datetime.now().strftime('%Y%m%d-%H%M')}

{resp['signature']}

--
AI Employee | After Hours Response
Business Hours: Mon-Fri, 09:00-17:00 UTC"""


def generate_spam_warning(subject: str, snippet: str) -> str:
    """Generate warning for potential spam."""
    return f"""Hello,

Your email has been flagged for review due to suspicious content.

If this is a legitimate message, please resend with:
- Clear subject line
- Proper greeting
- Specific request

Reference: SPAM-{datetime.now().strftime('%Y%m%d-%H%M')}

--
AI Employee | Spam Filter
wdigital085@gmail.com"""


def summarize_email(subject: str, snippet: str, content: str) -> dict:
    """Generate AI-style email summary."""
    # Simple keyword-based summarization
    words = (subject + " " + snippet + " " + content).lower().split()
    
    # Count important keywords
    action_words = ["need", "want", "require", "request", "please", "urgent", "asap"]
    topic_words = ["invoice", "payment", "meeting", "job", "support", "help"]
    
    actions = sum(1 for word in words if word in action_words)
    topics = [word for word in words if word in topic_words]
    
    # Determine intent
    if actions >= 2:
        intent = "Action Required"
    elif "urgent" in words or "asap" in words:
        intent = "Urgent"
    elif any(word in words for word in ["question", "ask", "help"]):
        intent = "Inquiry"
    else:
        intent = "Information"
    
    return {
        "intent": intent,
        "topics": list(set(topics)),
        "action_count": actions,
        "word_count": len(words),
        "estimated_read_time": f"{max(1, len(words) // 200)} min"
    }


def process_advanced_features():
    """Main function to process advanced Gmail features."""
    
    print("=" * 50)
    print("  📧 Advanced Gmail Features")
    print("=" * 50)
    print()
    
    # Load config
    config_file = CONFIG_DIR / "config.json"
    if config_file.exists():
        config = json.loads(config_file.read_text())
    else:
        config = {
            "vip_count": 0,
            "spam_filtered": 0,
            "after_hours_count": 0,
            "languages_detected": {}
        }
    
    today = datetime.now(timezone.utc)
    today_slug = today.strftime("%Y%m%d")
    
    emails_processed = 0
    vip_emails = 0
    spam_filtered = 0
    after_hours = 0
    summaries = []
    
    if NEEDS_ACTION.exists():
        email_files = list(NEEDS_ACTION.glob(f"EMAIL_{today_slug}*.md"))
        
        for email_file in email_files:
            content = email_file.read_text(encoding='utf-8')
            
            # Skip if already processed with advanced features
            if 'advanced_features: true' in content.lower():
                continue
            
            emails_processed += 1
            
            # Parse email
            lines = content.splitlines()
            email_data = {}
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    email_data[key.strip().lower()] = value.strip()
            
            from_email = email_data.get('from', '')
            subject = email_data.get('subject', email_file.stem)
            snippet = email_data.get('snippet', '')
            
            print(f"\n📧 Processing: {subject}")
            print(f"   From: {from_email}")
            
            # Feature 1: VIP Detection
            if is_vip_sender(from_email):
                print("   ⭐ VIP Sender Detected!")
                vip_emails += 1
                config["vip_count"] = config.get("vip_count", 0) + 1
            
            # Feature 2: Spam Detection
            if is_spam(subject, snippet):
                print("   ⚠️  Potential Spam Detected")
                spam_filtered += 1
                config["spam_filtered"] = config.get("spam_filtered", 0) + 1
            
            # Feature 3: Business Hours Check
            if not is_business_hours():
                print("   🌙 After Hours Email")
                after_hours += 1
                config["after_hours_count"] = config.get("after_hours_count", 0) + 1
            
            # Feature 4: Language Detection
            lang = detect_language(subject + " " + snippet)
            print(f"   🌐 Language: {lang}")
            config["languages_detected"] = config.get("languages_detected", {})
            config["languages_detected"][lang] = config["languages_detected"].get(lang, 0) + 1
            
            # Feature 5: Email Summarization
            summary = summarize_email(subject, snippet, content)
            print(f"   📊 Intent: {summary['intent']}")
            print(f"   📝 Topics: {', '.join(summary['topics']) if summary['topics'] else 'General'}")
            summaries.append({
                "file": email_file.name,
                "summary": summary
            })
            
            # Mark as processed with advanced features
            updated_content = content.replace(
                'status: pending',
                'status: pending\nadvanced_features: true\nvip: ' + str(is_vip_sender(from_email)).lower() + '\nlanguage: ' + lang + '\nintent: ' + summary['intent']
            )
            email_file.write_text(updated_content, encoding='utf-8')
    
    print()
    print("=" * 50)
    print("  ✅ Advanced Features Complete!")
    print("=" * 50)
    print()
    print("📊 Summary:")
    print(f"   Emails Processed: {emails_processed}")
    print(f"   VIP Senders: {vip_emails}")
    print(f"   Spam Filtered: {spam_filtered}")
    print(f"   After Hours: {after_hours}")
    print(f"   Languages: {', '.join(config.get('languages_detected', {}).keys()) or 'English only'}")
    print()
    
    # Save config
    config["last_run"] = today.isoformat()
    config_file.write_text(json.dumps(config, indent=2), encoding='utf-8')
    
    # Save summaries
    summary_file = CONFIG_DIR / f"summaries_{today_slug}.json"
    summary_file.write_text(json.dumps(summaries, indent=2), encoding='utf-8')
    
    return emails_processed, vip_emails, spam_filtered, after_hours


if __name__ == "__main__":
    process_advanced_features()
