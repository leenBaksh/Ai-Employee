#!/bin/bash
# setup_linkedin_automation.sh - Complete LinkedIn Automation Setup
# Run this to enable full LinkedIn automation

set -e

echo "=============================================="
echo "  💼 LinkedIn Full Automation Setup"
echo "=============================================="
echo ""

cd /mnt/d/Hackathon-00/Ai-Employee

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found!"
    exit 1
fi

echo "=== 1. Checking LinkedIn Configuration ==="
echo ""

# Check LinkedIn credentials
if grep -q "LINKEDIN_USER=" .env && ! grep -q "LINKEDIN_USER=$" .env; then
    LINKEDIN_USER=$(grep "LINKEDIN_USER=" .env | cut -d'=' -f2)
    echo "✅ LinkedIn User: $LINKEDIN_USER"
else
    echo "❌ LinkedIn user not configured"
    echo "   Edit .env and add: LINKEDIN_USER=your@email.com"
    exit 1
fi

if grep -q "LINKEDIN_PASSWORD=" .env && ! grep -q "LINKEDIN_PASSWORD=$" .env; then
    echo "✅ LinkedIn Password: configured"
else
    echo "⚠️  LinkedIn password not set (may use session)"
fi

# Check session directory
if [ -d "secrets/linkedin_session" ]; then
    echo "✅ Session directory exists"
else
    echo "📁 Creating session directory..."
    mkdir -p secrets/linkedin_session
fi

# Check setup complete marker
if [ -f "secrets/linkedin_session/.setup_complete" ]; then
    echo "✅ LinkedIn setup marker found"
else
    echo "⚠️  Setup marker not found - running setup..."
    uv run python -m watchers.linkedin_watcher --setup
fi

echo ""
echo "=== 2. Enabling LinkedIn Automation ==="
echo ""

# Enable LinkedIn in .env
if grep -q "LINKEDIN_ENABLED=true" .env; then
    echo "✅ LinkedIn already enabled"
else
    echo "📝 Enabling LinkedIn automation..."
    if grep -q "LINKEDIN_ENABLED=" .env; then
        sed -i 's/LINKEDIN_ENABLED=.*/LINKEDIN_ENABLED=true/' .env
    else
        echo "LINKEDIN_ENABLED=true" >> .env
    fi
    echo "✅ LinkedIn enabled"
fi

# Set max posts per day
if grep -q "LINKEDIN_MAX_POSTS_PER_DAY=" .env; then
    echo "✅ Max posts setting exists"
else
    echo "📝 Adding max posts setting..."
    echo "LINKEDIN_MAX_POSTS_PER_DAY=2" >> .env
fi

echo ""
echo "=== 3. Restarting Scheduler ==="
echo ""

# Restart scheduler to load LinkedIn automation
pkill -f "scheduler.py" 2>/dev/null || true
sleep 2

nohup uv run python -m scheduler > /tmp/scheduler.log 2>&1 &
sleep 3

if ps aux | grep -f "scheduler.py" | grep -v grep > /dev/null; then
    echo "✅ Scheduler restarted with LinkedIn automation"
else
    echo "❌ Failed to start scheduler"
    exit 1
fi

echo ""
echo "=== 4. Testing LinkedIn Digest ==="
echo ""

uv run python -c "
from scheduler import _generate_linkedin_daily_digest
digest = _generate_linkedin_daily_digest()
print(digest)
"

echo ""
echo "=============================================="
echo "  ✅ LinkedIn Automation Setup Complete!"
echo "=============================================="
echo ""
echo "📋 What's Now Active:"
echo ""
echo "  ✅ LinkedIn Watcher - Monitoring post queue"
echo "  ✅ Daily Digest - Sent at 19:00 UTC (12 AM PKT)"
echo "  ✅ Auto-Posting - Max 2 posts/day"
echo "  ✅ Engagement Tracking - Ready"
echo ""
echo "📊 How It Works:"
echo ""
echo "  1. Create posts in /To_Post/LinkedIn/"
echo "  2. Approve posts → move to /Approved/"
echo "  3. Orchestrator creates trigger in /Scheduled/"
echo "  4. Run /post-linkedin in Claude Code"
echo "  5. AI posts via Playwright MCP browser automation"
echo ""
echo "📱 Daily Digest Includes:"
echo ""
echo "  - Posts in queue"
echo "  - Scheduled posts"
echo "  - Posts published today"
echo "  - Account status"
echo ""
echo "🚀 Next Steps:"
echo ""
echo "  1. Create LinkedIn content"
echo "  2. Approve posts for publishing"
echo "  3. Watch for daily digest at 19:00 UTC"
echo ""
echo "=============================================="
