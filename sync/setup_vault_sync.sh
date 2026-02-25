#!/usr/bin/env bash
# sync/setup_vault_sync.sh — Initialize git-based vault sync (Platinum Tier)
#
# Sets up the Obsidian vault as a git repository for Cloud↔Local sync.
# Secrets (.env, credentials, tokens) are NEVER synced — .gitignore enforces this.
#
# Usage:
#   bash sync/setup_vault_sync.sh
#   bash sync/setup_vault_sync.sh --remote git@github.com:youruser/ai-employee-vault.git

set -euo pipefail

VAULT_DIR="${VAULT_PATH:-./AI_Employee_Vault}"
REMOTE="${1:-}"

echo "=== AI Employee Vault Sync Setup (Platinum Tier) ==="
echo "Vault: $VAULT_DIR"

# 1. Initialize git repo in vault
cd "$VAULT_DIR"
if [ ! -d .git ]; then
    git init
    echo "Git repo initialized in vault."
else
    echo "Git repo already exists."
fi

# 2. Write vault-specific .gitignore (secrets never sync)
cat > .gitignore << 'EOF'
# ──────────────────────────────────────────────
# AI Employee Vault — Sync Security Policy
# Platinum Tier: secrets NEVER sync to cloud
# ──────────────────────────────────────────────

# Credentials and secrets
.env
secrets/
*.json.bak
credentials.json
token.json
*.key
*.pem
*.p12

# LinkedIn session storage (contains auth tokens)
linkedin_session/
*.session

# WhatsApp local session data
whatsapp_session/

# Large binary files
*.mp4
*.mp3
*.zip
*.tar.gz

# OS/editor artifacts
.DS_Store
Thumbs.db
*.swp
.obsidian/workspace.json

# Playwright browser data (large, local only)
playwright-browsers/
EOF

echo ".gitignore written (secrets excluded)."

# 3. Initial commit
git add -A
git diff --cached --quiet || git commit -m "chore: initialize vault sync (Platinum Tier)"

# 4. Add remote if provided
if [ -n "$REMOTE" ]; then
    git remote remove origin 2>/dev/null || true
    git remote add origin "$REMOTE"
    echo "Remote added: $REMOTE"
    echo "Run 'bash sync/sync_up.sh' to push to cloud."
else
    echo ""
    echo "No remote specified. To add one:"
    echo "  git -C $VAULT_DIR remote add origin <git-remote-url>"
    echo "  bash sync/sync_up.sh"
fi

echo ""
echo "=== Setup complete ==="
echo "Local Agent: bash sync/sync_up.sh   (push changes to cloud)"
echo "Cloud Agent: bash sync/sync_down.sh (pull latest from local)"
