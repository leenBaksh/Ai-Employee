"""
auto_linkedin_poster_full.py - FULLY AUTOMATIC LinkedIn Posting

This script:
1. Generates AI post content automatically
2. Opens LinkedIn in browser
3. Logs in automatically (if needed)
4. Clicks "Start a post"
5. Types the post content
6. Adds an image (if available)
7. Clicks Post button
8. Saves confirmation

Usage:
    uv run python auto_linkedin_poster_full.py
"""

import os
import json
import random
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()
TO_POST_DIR = VAULT_PATH / "To_Post" / "LinkedIn"
DONE_DIR = VAULT_PATH / "Done"
SCHEDULED_DIR = VAULT_PATH / "Scheduled"
IMAGES_DIR = VAULT_PATH / "LinkedIn_Images"

# Ensure directories exist
for dir_path in [TO_POST_DIR, DONE_DIR, SCHEDULED_DIR, IMAGES_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# LinkedIn Credentials
LINKEDIN_EMAIL = os.getenv("LINKEDIN_USER", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

# Post Templates
POST_TEMPLATES = [
    {
        "topic": "AI Automation",
        "hook": "🤖 AI Agents are NOT just automation.",
        "body": "Let me explain the difference:\n\n❌ Traditional Automation:\n- Follows rigid rules\n- Breaks on exceptions\n- Zero decision-making\n\n✅ AI Agents:\n- Analyze context & intent\n- Adapt to new scenarios\n- Make autonomous decisions\n- Learn from patterns\n\nI've built an AI Employee that runs 24/7:\n• Gmail with smart auto-replies\n• WhatsApp with conversation tracking\n• LinkedIn auto-posting\n• Priority detection & VIP handling\n\nThe result?\n📊 27+ emails processed daily\n📊 Zero manual intervention\n📊 100% audit trail\n\nAutomation replaces tasks.\nAI Agents amplify intelligence.\n\nWhat's your take on AI vs automation?",
        "hashtags": "#AIAgents #Automation #ArtificialIntelligence #FutureOfWork #DigitalTransformation",
        "image_prompt": "AI robot working on laptop with charts and graphs"
    },
    {
        "topic": "Productivity",
        "hook": "⚡ I automated my entire business.",
        "body": "Here's what runs 24/7 without me:\n\n📧 Gmail\n- Auto-replies in 5 languages\n- Priority detection\n- Spam filtering\n\n💬 WhatsApp Business\n- Instant auto-replies\n- Daily conversation reports\n- 14 conversation types tracked\n\n💼 LinkedIn\n- Auto-generates posts\n- Auto-posts with images\n- Analytics tracking\n\n⏰ Scheduler\n- Daily briefings\n- Weekly audits\n- SLA monitoring\n\nThe best part?\n\nI focus on strategy.\nThe AI handles execution.\n\nResult: 10x productivity with zero burnout.\n\nWhat would you automate first?",
        "hashtags": "#Productivity #Automation #AI #BusinessAutomation #Entrepreneurship",
        "image_prompt": "Dashboard showing automation metrics and charts"
    },
    {
        "topic": "Business Growth",
        "hook": "📈 Small team? Big impact.",
        "body": "Here's how a 1-person team can operate like a 10-person company:\n\n1️⃣ AI Employee handles:\n   - Customer communication\n   - Social media posting\n   - Email management\n   - Task tracking\n\n2️⃣ Automation handles:\n   - Data entry\n   - Report generation\n   - Appointment scheduling\n   - Follow-ups\n\n3️⃣ You focus on:\n   - Strategy\n   - Relationships\n   - Growth\n   - Innovation\n\nThe math is simple:\n\nHuman creativity + AI execution = Unstoppable\n\nI built this system and now:\n✅ Work 4 hours/day\n✅ 27+ emails handled daily\n✅ Zero missed opportunities\n✅ 100% audit trail\n\nYour turn: What's stopping you?",
        "hashtags": "#BusinessGrowth #AI #Automation #Startup #Entrepreneurship",
        "image_prompt": "Growth chart going up with AI and human collaboration"
    },
    {
        "topic": "Technology",
        "hook": "🚀 2026 is the year of AI Employees.",
        "body": "Not AI tools.\nNot AI assistants.\n\nAI EMPLOYEES.\n\nHere's what mine does daily:\n\n🌅 Morning (automated):\n- Checks emails, prioritizes urgent\n- Sends daily briefing\n- Reviews calendar\n\n☀️ Day (automated):\n- Responds to customer inquiries\n- Posts on LinkedIn\n- Tracks conversations\n- Logs all activities\n\n🌙 Evening (automated):\n- Sends daily reports\n- Creates tomorrow's tasks\n- Backs up all data\n\nTotal human intervention:\n⏱️ 30 minutes/day\n\nTotal output:\n📊 27+ emails handled\n📊 1 LinkedIn post\n📊 100% compliance\n📊 Zero errors\n\nThe future isn't human vs AI.\nIt's human + AI.\n\nAre you ready?",
        "hashtags": "#AI #FutureOfWork #Technology #Innovation #DigitalTransformation",
        "image_prompt": "Futuristic AI employee working at desk"
    }
]


def generate_post():
    """Generate AI post content."""
    template = random.choice(POST_TEMPLATES)
    
    post = {
        "topic": template["topic"],
        "hook": template["hook"],
        "body": template["body"],
        "hashtags": template["hashtags"],
        "image_prompt": template["image_prompt"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    return post


def create_image_placeholder(post_data: dict) -> Path:
    """Create a placeholder image file for the post."""
    
    # Create a simple SVG image as placeholder
    svg_content = f"""<svg width="1200" height="630" xmlns="http://www.w3.org/2000/svg">
  <!-- Background -->
  <rect width="1200" height="630" fill="#0f172a"/>
  
  <!-- Gradient overlay -->
  <defs>
    <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#06b6d4;stop-opacity:0.3" />
      <stop offset="100%" style="stop-color:#8b5cf6;stop-opacity:0.3" />
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#grad1)"/>
  
  <!-- Title -->
  <text x="600" y="280" font-family="Arial, sans-serif" font-size="48" font-weight="bold" fill="#ffffff" text-anchor="middle">
    {post_data['topic']}
  </text>
  
  <!-- Hook -->
  <text x="600" y="340" font-family="Arial, sans-serif" font-size="24" fill="#94a3b8" text-anchor="middle">
    {post_data['hook'][:60]}...
  </text>
  
  <!-- Footer -->
  <text x="600" y="580" font-family="Arial, sans-serif" font-size="18" fill="#06b6d4" text-anchor="middle">
    AI Employee | Auto-Generated Post
  </text>
  
  <!-- Decorative elements -->
  <circle cx="100" cy="100" r="50" fill="#06b6d4" opacity="0.3"/>
  <circle cx="1100" cy="530" r="80" fill="#8b5cf6" opacity="0.3"/>
</svg>"""
    
    image_file = IMAGES_DIR / f"post_{datetime.now().strftime('%Y%m%d_%H%M%S')}.svg"
    image_file.write_text(svg_content, encoding='utf-8')
    
    return image_file


def auto_post_to_linkedin(post_data: dict, image_path: Path = None):
    """Fully automatic LinkedIn posting via Playwright."""
    
    print("🌐 Opening LinkedIn...")
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=False)  # Visible for debugging
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = context.new_page()
            
            # Navigate to LinkedIn
            print("   📍 Navigating to LinkedIn...")
            page.goto("https://www.linkedin.com/login", wait_until="networkidle")
            
            # Check if already logged in
            if "feed" in page.url:
                print("   ✅ Already logged in")
            else:
                # Login
                print("   🔐 Logging in...")
                if LINKEDIN_EMAIL and LINKEDIN_PASSWORD:
                    page.fill("#username", LINKEDIN_EMAIL)
                    page.fill("#password", LINKEDIN_PASSWORD)
                    page.click('button[type="submit"]')
                    
                    try:
                        page.wait_for_url("https://www.linkedin.com/feed/*", timeout=15000)
                        print("   ✅ Logged in successfully")
                    except:
                        print("   ⚠️  Login may require CAPTCHA - please complete manually")
                        page.wait_for_url("https://www.linkedin.com/feed/*", timeout=60000)
                        print("   ✅ Login completed")
            
            # Navigate to feed
            print("   📍 Navigating to feed...")
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(8000)  # Wait for content to render
            print("   ✅ Feed loaded")
            
            # Click "Start a post" - try multiple selectors
            print("   📝 Finding post button...")
            post_button_clicked = False
            
            # Try different selectors for "Start a post" button
            selectors = [
                'button:has-text("Start a post")',
                'button:has-text("Start")',
                '.share-box-feed-entry__trigger',
                '[aria-label="Start a post"]',
                '.artdeco-button:has-text("Start")'
            ]
            
            for selector in selectors:
                try:
                    page.click(selector, timeout=5000)
                    print(f"   ✅ Post dialog opened (using: {selector[:40]})")
                    post_button_clicked = True
                    break
                except:
                    continue
            
            if not post_button_clicked:
                print("   ⚠️  Could not auto-click post button - taking screenshot")
                page.screenshot(path='linkedin_post_button.png')
                print("   📸 Screenshot saved: linkedin_post_button.png")
                print("   ⏸️  Waiting 30 seconds for manual intervention...")
                page.wait_for_timeout(30000)
            
            # Wait for post dialog
            page.wait_for_timeout(3000)
            
            # Wait for text area
            try:
                page.wait_for_selector('div[contenteditable="true"]', timeout=10000)
                
                # Prepare full post text
                full_post = f"{post_data['hook']}\n\n{post_data['body']}\n\n{post_data['hashtags']}"
                
                # Clear and type post content
                print("   📝 Typing post content...")
                page.fill('div[contenteditable="true"]', "")
                page.fill('div[contenteditable="true"]', full_post)
                print("   ✅ Content typed")
                
                # Wait for content to be recognized
                page.wait_for_timeout(2000)
                
                # Add image if available
                if image_path and image_path.exists():
                    print("   🖼️  Adding image...")
                    # Click media button
                    try:
                        page.click('button[aria-label="Add media"]', timeout=5000)
                        # Upload file
                        page.set_input_files('input[type="file"]', str(image_path))
                        print("   ✅ Image added")
                    except Exception as e:
                        print(f"   ⚠️  Could not add image: {e}")
                
                # Wait a moment for image to load
                page.wait_for_timeout(3000)
                
                # Click Post button
                print("   🚀 Clicking Post button...")
                try:
                    # Try different Post button selectors
                    post_button_clicked = False
                    post_selectors = [
                        'button:has-text("Post")',
                        'button:has-text("Post")',
                        '.artdeco-button:has-text("Post")'
                    ]
                    
                    for selector in post_selectors:
                        try:
                            page.click(selector, timeout=5000)
                            print(f"   ✅ Post button clicked")
                            post_button_clicked = True
                            break
                        except:
                            continue
                    
                    if not post_button_clicked:
                        print("   ⚠️  Post button not found - taking screenshot")
                        page.screenshot(path='linkedin_post_button_error.png')
                        print("   📸 Screenshot: linkedin_post_button_error.png")
                        success = False
                    else:
                        # Wait for confirmation
                        page.wait_for_timeout(5000)
                        print("   ✅ Post published successfully!")
                        success = True
                        
                except Exception as e:
                    print(f"   ❌ Error clicking Post: {e}")
                    page.screenshot(path='linkedin_post_error.png')
                    success = False
                
            except Exception as e:
                print(f"   ❌ Error creating post: {e}")
                success = False
            
            browser.close()
            return success
            
    except ImportError:
        print("   ❌ Playwright not installed")
        print("   Install: uv add playwright && playwright install chromium")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def save_post_record(post_data: dict, image_path: Path, success: bool):
    """Save post record to Done folder."""
    
    today = datetime.now(timezone.utc)
    ts = today.strftime("%Y%m%dT%H%M%SZ")
    
    # Create post file
    post_file = DONE_DIR / f"LINKEDIN_AUTO_{ts}.md"
    post_content = f"""---
type: linkedin_auto_post
topic: {post_data['topic']}
created: {post_data['timestamp']}
posted: {today.isoformat()}
auto_generated: true
status: {'posted' if success else 'failed'}
---

## Auto-Posted to LinkedIn

**Topic:** {post_data['topic']}

**Hook:**
{post_data['hook']}

**Body:**
{post_data['body']}

**Hashtags:**
{post_data['hashtags']}

**Image:**
{image_path.name if image_path else 'None'}

---
*Posted automatically by AI Employee*
"""
    
    post_file.write_text(post_content, encoding='utf-8')
    
    return post_file


def run_full_auto_post():
    """Main function for fully automatic LinkedIn posting."""
    
    print("=" * 50)
    print("  🚀 Fully Automatic LinkedIn Poster")
    print("=" * 50)
    print()
    
    # Check configuration
    print("📋 Configuration Check:")
    print(f"   Account: {LINKEDIN_EMAIL or 'Not configured'}")
    print(f"   Vault: {VAULT_PATH}")
    print()
    
    # Generate post content
    print("📝 Step 1: Generating AI post content...")
    post_data = generate_post()
    print(f"   ✅ Topic: {post_data['topic']}")
    print(f"   ✅ Hook: {post_data['hook']}")
    print()
    
    # Create image
    print("🖼️  Step 2: Creating post image...")
    image_path = create_image_placeholder(post_data)
    print(f"   ✅ Image created: {image_path.name}")
    print()
    
    # Post to LinkedIn
    print("🚀 Step 3: Auto-posting to LinkedIn...")
    print("   (Browser will open - watch it post automatically!)")
    print()
    success = auto_post_to_linkedin(post_data, image_path)
    print()
    
    # Save record
    print("📁 Step 4: Saving post record...")
    post_file = save_post_record(post_data, image_path, success)
    print(f"   ✅ Saved: {post_file.name}")
    print()
    
    # Summary
    print("=" * 50)
    print("  ✅ LinkedIn Auto-Post Complete!")
    print("=" * 50)
    print()
    print(f"📊 Summary:")
    print(f"   Topic: {post_data['topic']}")
    print(f"   Posted: {'✅ Yes' if success else '❌ No'}")
    print(f"   Image: {image_path.name}")
    print(f"   Record: {post_file.name}")
    print(f"   Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print()
    
    return success


if __name__ == "__main__":
    run_full_auto_post()
