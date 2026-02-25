# Skill: Deploy Cloud

**Command:** `/deploy-cloud`
**Tier:** Platinum

## Purpose
Guide setup and deployment of the Cloud Agent to a remote VM (Oracle Cloud Free Tier,
AWS, or any Ubuntu VM). Walks through the end-to-end Platinum deployment.

## When to Use
- User asks "deploy to cloud", "setup cloud agent", "how do I run this on a server"
- First-time Platinum deployment
- Re-deploying after a cloud VM was replaced

## Steps

### Step 1 — Read current config
Check what cloud settings are in `.env`:
```bash
grep -E "CLOUD_|VAULT_SYNC" .env | sed 's/=.*/=<set>/'
```

### Step 2 — Confirm cloud VM details
Ask the user:
- Cloud provider and region (Oracle Cloud, AWS, etc.)
- VM IP address or hostname
- SSH username (ubuntu, opc, ec2-user, etc.)
- SSH key path

### Step 3 — Validate SSH access
```bash
ssh -o ConnectTimeout=5 <user>@<host> "echo connected"
```

### Step 4 — Deploy code
```bash
# Copy project to VM (excluding secrets)
rsync -avz --exclude='.env' --exclude='secrets/' --exclude='.venv*' \
  /mnt/d/Hackathon-00/Ai-Employee/ <user>@<host>:~/ai-employee/
```

### Step 5 — Run setup on VM
```bash
ssh <user>@<host> "cd ~/ai-employee && bash cloud/setup_cloud.sh"
```

### Step 6 — Configure vault sync
On the VM, setup git remote for vault sync:
```bash
ssh <user>@<host> "cd ~/ai-employee && bash sync/setup_vault_sync.sh --remote <git-url>"
```

### Step 7 — Start cloud agent
```bash
ssh <user>@<host> "sudo systemctl start ai-employee-cloud"
ssh <user>@<host> "sudo systemctl status ai-employee-cloud"
```

### Step 8 — Verify
Wait 2 minutes, then check:
```bash
cat AI_Employee_Vault/Signals/HEALTH_cloud-01.json
```
Should show `"status": "online"`.

### Step 9 — Report
```
✅ Cloud Agent deployed
🌐 Host: <hostname>
🆔 Agent ID: cloud-01
📡 Vault sync: every 5 minutes via cron
🏥 Health: online
```

## Security Checklist
- [ ] .env NOT copied to cloud VM
- [ ] Only markdown files synced via git
- [ ] Cloud VM has firewall: only SSH (port 22) open
- [ ] Cloud Agent role = draft-only (no execution credentials)
