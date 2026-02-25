#!/usr/bin/env bash
# cloud/setup_cloud.sh — Bootstrap AI Employee on a Cloud VM (Platinum Tier)
#
# Run this ONCE on a fresh Oracle Cloud / AWS / other VM.
# Tested on Ubuntu 22.04 LTS.
#
# Usage:
#   git clone <your-repo> ai-employee
#   cd ai-employee
#   bash cloud/setup_cloud.sh

set -euo pipefail

echo "=== AI Employee Cloud Setup (Platinum Tier) ==="
echo "Host: $(hostname)"
echo "Date: $(date -u)"

# 1. System dependencies
echo ""
echo "--- Installing system dependencies ---"
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip curl git tmux

# 2. Install uv
echo ""
echo "--- Installing uv package manager ---"
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# 3. Install Python dependencies
echo ""
echo "--- Installing Python dependencies ---"
uv sync

# 4. Create cloud-specific .env (NEVER copy local .env with secrets)
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "IMPORTANT: Edit .env and set cloud-specific values:"
    echo "  VAULT_PATH=./AI_Employee_Vault"
    echo "  CLOUD_AGENT_ID=cloud-01"
    echo "  CLOUD_AGENT_INTERVAL=60"
    echo "  DRY_RUN=false"
    echo ""
    echo "DO NOT copy SMTP_PASSWORD, ODOO_PASSWORD, or LinkedIn credentials to cloud."
    echo "The Cloud Agent is draft-only — it does not need those secrets."
fi

# 5. Setup vault sync
echo ""
echo "--- Setting up vault sync ---"
bash sync/setup_vault_sync.sh

# 6. Setup systemd service for Cloud Agent (optional)
echo ""
echo "--- Creating systemd service ---"
INSTALL_DIR="$(pwd)"
USER_NAME="$(whoami)"

cat > /tmp/ai-employee-cloud.service << EOF
[Unit]
Description=AI Employee Cloud Agent (Platinum Tier)
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$INSTALL_DIR
ExecStart=$HOME/.local/bin/uv run python cloud_agent.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo cp /tmp/ai-employee-cloud.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ai-employee-cloud
echo "Systemd service installed: ai-employee-cloud"

# 7. Setup vault sync cron (every 5 minutes)
echo ""
echo "--- Setting up vault sync cron ---"
CRON_JOB="*/5 * * * * cd $INSTALL_DIR && bash sync/sync_down.sh >> /tmp/vault-sync.log 2>&1"
( crontab -l 2>/dev/null | grep -v "sync_down.sh"; echo "$CRON_JOB" ) | crontab -
echo "Cron job added: sync every 5 minutes"

echo ""
echo "=== Cloud Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env with VAULT_SYNC_BRANCH and git remote for vault"
echo "  2. Run: bash sync/setup_vault_sync.sh --remote <git-url>"
echo "  3. Start agent: sudo systemctl start ai-employee-cloud"
echo "  4. Check logs: journalctl -u ai-employee-cloud -f"
