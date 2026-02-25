# Skill: Sync Vault

**Command:** `/sync-vault`
**Tier:** Platinum

## Purpose
Synchronize the Obsidian vault between Local and Cloud agents using git.
Ensures Cloud Agent has latest tasks, and Local Agent gets Cloud Agent's drafts.

## When to Use
- After completing a batch of tasks (push local changes to cloud)
- After approving/rejecting cloud-drafted items
- When Cloud Agent health signal is stale (manual pull)
- User says "sync vault", "push to cloud", "pull from cloud"

## Steps

### Step 1 — Check sync configuration
```bash
git -C AI_Employee_Vault remote get-url origin 2>/dev/null || echo "No remote configured"
git -C AI_Employee_Vault status --short | head -20
```

If no remote: instruct user to run `bash sync/setup_vault_sync.sh --remote <git-url>`.

### Step 2 — Push local changes
```bash
bash sync/sync_up.sh
```

Report: how many files changed, commit hash.

### Step 3 — Check for cloud updates
Read `AI_Employee_Vault/Updates/` for signals from the Cloud Agent.
List any new UPDATE_*.md files and summarize what the Cloud Agent has done.

### Step 4 — Clear processed update signals
Move processed UPDATE_*.md files to Done/.

### Step 5 — Report
```
✅ Vault synced
📤 Pushed: N files changed
📥 Cloud updates received: N
🏥 Cloud Agent status: online/offline (last seen Xs ago)
```

## Security Note
`.env`, `secrets/`, and credential files are excluded from sync via vault `.gitignore`.
Only markdown and JSON state files are ever synced to the cloud.
