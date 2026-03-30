#!/bin/bash
# start_full_automation.sh - Start all AI Employee services for full automation
# Run this script to start the complete AI Employee system

set -e

echo "========================================"
echo "  AI Employee - Full Automation Start"
echo "========================================"
echo ""

# Change to project directory
cd /mnt/d/Hackathon-00/Ai-Employee

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found!"
    echo "   Please copy .env.example to .env and configure your credentials."
    exit 1
fi

echo "✅ Configuration loaded from .env"
echo ""

# Function to check if a process is running
is_running() {
    pgrep -f "$1" > /dev/null 2>&1
}

# Function to start a service
start_service() {
    local name="$1"
    local command="$2"
    local log_file="$3"
    
    if is_running "$name"; then
        echo "⚠️  $name is already running"
    else
        echo "🚀 Starting $name..."
        nohup $command > "$log_file" 2>&1 &
        sleep 2
        if is_running "$name"; then
            echo "✅ $name started (PID: $!)"
        else
            echo "❌ Failed to start $name"
            return 1
        fi
    fi
}

echo "========================================"
echo "  Starting Core Services"
echo "========================================"
echo ""

# 1. Start WhatsApp Webhook Server (Cloud API mode)
if grep -q "WHATSAPP_ACCESS_TOKEN=" .env && ! grep -q "WHATSAPP_ACCESS_TOKEN=$" .env; then
    start_service "whatsapp_webhook" "uv run python -m watchers.whatsapp_webhook_server" "/tmp/whatsapp_webhook.log"
else
    echo "⚠️  WhatsApp Cloud API not configured - skipping webhook server"
fi

# 2. Start WhatsApp Web Watcher (fallback if Cloud API not configured)
if ! is_running "whatsapp_webhook"; then
    start_service "whatsapp_watcher" "uv run python -m watchers.whatsapp_watcher" "/tmp/whatsapp_watcher.log"
fi

# 3. Start Gmail Watcher
if grep -q "GMAIL_CREDENTIALS_PATH=" .env && [ -f "./secrets/gmail_credentials.json" ]; then
    start_service "gmail_watcher" "uv run python -m watchers.gmail_watcher" "/tmp/gmail_watcher.log"
else
    echo "⚠️  Gmail credentials not found - skipping Gmail watcher"
fi

# 4. Start LinkedIn Watcher
if grep -q "LINKEDIN_SESSION_PATH=" .env; then
    start_service "linkedin_watcher" "uv run python -m watchers.linkedin_watcher" "/tmp/linkedin_watcher.log"
else
    echo "⚠️  LinkedIn session not configured - skipping LinkedIn watcher"
fi

# 5. Start Scheduler
start_service "scheduler" "uv run python scheduler.py" "/tmp/scheduler.log"

# 6. Start Process Watchdog (auto-restart failed services)
start_service "watchdog" "uv run python process_watchdog.py" "/tmp/watchdog.log"

echo ""
echo "========================================"
echo "  Starting Dashboard"
echo "========================================"
echo ""

# 7. Start Dashboard Server (Flask backend)
start_service "dashboard_server" "uv run python dashboard_server.py" "/tmp/dashboard_server.log"

# 8. Start Next.js Frontend
if is_running "next dev"; then
    echo "⚠️  Next.js frontend is already running"
else
    echo "🚀 Starting Next.js frontend..."
    cd dashboard-ui
    nohup npm run dev > /tmp/nextjs.log 2>&1 &
    sleep 5
    cd ..
    if is_running "next dev"; then
        echo "✅ Next.js frontend started"
    else
        echo "❌ Failed to start Next.js frontend"
    fi
fi

echo ""
echo "========================================"
echo "  Full Automation Started!"
echo "========================================"
echo ""
echo "📊 Dashboard: http://localhost:8888"
echo "🌐 Frontend:  http://localhost:3000"
echo ""
echo "Services running:"
echo "  ✅ Scheduler (daily briefings, weekly audits)"
echo "  ✅ WhatsApp (Cloud API webhook + auto-reply)"
echo "  ✅ Process Watchdog (auto-restart on failure)"
echo "  ✅ Dashboard Server (Flask backend)"
echo "  ✅ Next.js Frontend (React UI)"
echo ""
echo "Optional services (if configured):"
echo "  📧 Gmail Watcher"
echo "  💼 LinkedIn Watcher"
echo ""
echo "To stop all services:"
echo "  pkill -f 'dashboard_server.py'"
echo "  pkill -f 'scheduler.py'"
echo "  pkill -f 'whatsapp_webhook'"
echo "  pkill -f 'whatsapp_watcher'"
echo "  pkill -f 'process_watchdog'"
echo "  pkill -f 'next dev'"
echo ""
echo "View logs:"
echo "  tail -f /tmp/whatsapp_webhook.log"
echo "  tail -f /tmp/scheduler.log"
echo "  tail -f /tmp/dashboard_server.log"
echo ""
