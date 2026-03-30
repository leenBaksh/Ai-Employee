#!/bin/bash
# linkedin_status.sh - Check LinkedIn automation status and analytics

echo "=============================================="
echo "  💼 LinkedIn Automation Status"
echo "=============================================="
echo ""

cd /mnt/d/Hackathon-00/Ai-Employee

echo "📊 Content Pipeline:"
echo ""

# Count posts in each stage
TO_POST=$(ls -1 AI_Employee_Vault/To_Post/LinkedIn/*.md 2>/dev/null | wc -l)
SCHEDULED=$(ls -1 AI_Employee_Vault/Scheduled/LINKEDIN_*.md 2>/dev/null | wc -l)
APPROVED=$(ls -1 AI_Employee_Vault/Approved/LINKEDIN_*.md 2>/dev/null | wc -l)
DONE=$(ls -1 AI_Employee_Vault/Done/LINKEDIN_*.md 2>/dev/null | wc -l)

echo "  📝 In Queue:      $TO_POST"
echo "  ⏳ Scheduled:     $SCHEDULED"
echo "  ✅ Approved:      $APPROVED"
echo "  📤 Posted Total:  $DONE"
echo ""

echo "📈 This Week's Activity:"
echo ""

# Count posts this week
WEEK_START=$(date -d "last monday" +%Y%m%d 2>/dev/null || date +%Y%m%d)
THIS_WEEK=$(ls -1 AI_Employee_Vault/Done/LINKEDIN_${WEEK_START}*.md 2>/dev/null | wc -l)

echo "  Posts This Week: $THIS_WEEK / 10 (5 days × 2/day)"
echo ""

echo "👥 Account Info:"
echo ""

# Get account from .env
LINKEDIN_USER=$(grep "LINKEDIN_USER=" .env | cut -d'=' -f2)
LINKEDIN_ENABLED=$(grep "LINKEDIN_ENABLED=" .env | cut -d'=' -f2)

echo "  Account: $LINKEDIN_USER"
echo "  Status:  $LINKEDIN_ENABLED"
echo ""

echo "⏰ Schedule:"
echo ""
echo "  Daily Digest: 19:00 UTC (00:00 AM PKT)"
echo "  Max Posts:    2 per day"
echo ""

echo "📋 Recent Posts:"
echo ""
ls -lt AI_Employee_Vault/To_Post/LinkedIn/*.md 2>/dev/null | head -5 | while read line; do
    echo "  $line"
done
echo ""

echo "=============================================="
echo "  🚀 Quick Commands:"
echo "=============================================="
echo ""
echo "  Create Post:  cd AI_Employee_Vault/To_Post/LinkedIn/"
echo "  Approve:      mv POST_*.md ../Approved/"
echo "  Post:         /post-linkedin (in Claude Code)"
echo "  View Digest:  Check WhatsApp at 19:00 UTC"
echo ""
echo "=============================================="
