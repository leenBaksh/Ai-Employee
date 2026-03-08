#!/usr/bin/env bash
# setup_local_pm2.sh — Start AI Employee as persistent PM2 daemons (local / WSL2)
#
# Prerequisites:
#   npm install -g pm2
#
# Usage:
#   bash scripts/setup_local_pm2.sh
#   bash scripts/setup_local_pm2.sh --with-gmail   # also start Gmail watcher

set -e

PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "=== AI Employee PM2 Setup ==="
echo "Project: $PROJ"
echo ""

# 1. Check PM2
if ! command -v pm2 &>/dev/null; then
    echo "ERROR: PM2 not found. Install with: npm install -g pm2"
    exit 1
fi

# 2. Stop any existing processes
pm2 delete ecosystem.config.js 2>/dev/null || true

# 3. Create logs dir
mkdir -p "$PROJ/logs"

# 4. Start core processes
echo "--- Starting AI Employee processes ---"
if [[ "$1" == "--with-gmail" ]]; then
    # Uncomment gmail-watcher section first
    sed -i 's|// {$|{|g; s|//   name:.*"gmail-watcher"|  name: "gmail-watcher"|' "$PROJ/ecosystem.config.js" 2>/dev/null || true
    pm2 start "$PROJ/ecosystem.config.js"
else
    pm2 start "$PROJ/ecosystem.config.js"
fi

# 5. Save process list for reboot persistence
pm2 save
echo ""

# 6. Setup startup hook (OS-specific)
echo "--- Setting up startup persistence ---"
echo "Run the following command to enable auto-start on reboot:"
echo ""
pm2 startup 2>&1 | grep -E "sudo|systemctl" || true
echo ""

# 7. Status
pm2 status
echo ""
echo "=== Setup complete ==="
echo ""
echo "Commands:"
echo "  pm2 status              — check all processes"
echo "  pm2 logs                — tail all logs"
echo "  pm2 logs orchestrator   — tail one process"
echo "  pm2 restart all         — restart everything"
echo "  pm2 monit               — live dashboard"
