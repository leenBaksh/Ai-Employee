#!/usr/bin/env bash
# sync/sync_down.sh — Pull vault changes from Local Agent to Cloud (Platinum Tier)
#
# Run this on the CLOUD VM to get latest tasks from Local Agent.
# Designed to be run in a cron job every 5 minutes on the cloud VM:
#   */5 * * * * /path/to/ai-employee/sync/sync_down.sh >> /var/log/vault-sync.log 2>&1
#
# Usage: bash sync/sync_down.sh

set -euo pipefail

VAULT_DIR="${VAULT_PATH:-./AI_Employee_Vault}"
BRANCH="${VAULT_SYNC_BRANCH:-main}"

cd "$VAULT_DIR"

if [ ! -d .git ]; then
    echo "ERROR: Vault is not a git repo. Run setup_vault_sync.sh first."
    exit 1
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Syncing vault DOWN (Cloud ← Local)..."

# Stash any local cloud agent writes before pulling
git stash push -m "cloud-agent-stash" --include-untracked 2>/dev/null || true

if git remote get-url origin &>/dev/null; then
    git fetch origin "$BRANCH"
    git merge "origin/$BRANCH" --no-edit --strategy-option=theirs
    echo "Pulled from origin/$BRANCH"
else
    echo "WARNING: No remote configured. Nothing to pull."
fi

# Re-apply cloud agent's local writes
git stash pop 2>/dev/null || true

echo "Sync DOWN complete."
