#!/usr/bin/env bash
# sync/sync_up.sh — Push vault changes from Local Agent to Cloud (Platinum Tier)
#
# Run this on the LOCAL machine after completing tasks.
# Cloud Agent will pull these changes on its next sync_down cycle.
#
# Usage: bash sync/sync_up.sh

set -euo pipefail

VAULT_DIR="${VAULT_PATH:-./AI_Employee_Vault}"
BRANCH="${VAULT_SYNC_BRANCH:-main}"

cd "$VAULT_DIR"

if [ ! -d .git ]; then
    echo "ERROR: Vault is not a git repo. Run setup_vault_sync.sh first."
    exit 1
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Syncing vault UP (Local → Cloud)..."

git add -A

if git diff --cached --quiet; then
    echo "No changes to sync."
    exit 0
fi

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
git commit -m "sync: local agent update @ $TIMESTAMP"

if git remote get-url origin &>/dev/null; then
    git push origin "$BRANCH"
    echo "Pushed to origin/$BRANCH"
else
    echo "WARNING: No remote configured. Changes committed locally only."
    echo "Add a remote: git -C $VAULT_DIR remote add origin <url>"
fi

echo "Sync UP complete."
