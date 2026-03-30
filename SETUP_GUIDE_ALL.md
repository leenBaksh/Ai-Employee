# 🚀 AI Employee - Complete Setup Guide

## Phase 1: Gmail Authentication ⏳

### Status: NEEDS YOUR INPUT

**Gmail setup requires browser authentication:**

1. **Open this URL in your browser:**
   ```
   Run: uv run gmail-watcher --setup
   ```

2. **A URL will be shown** - copy it

3. **Open in Windows browser** (since you're on WSL2)

4. **Sign in to Google** (wdigital085@gmail.com)

5. **Grant permissions**

6. **Copy the redirect URL** from the browser

7. **Paste it back** in the terminal

---

## Phase 2: LinkedIn Re-authentication 📊

### Status: NEEDS YOUR INPUT

**LinkedIn setup requires email input:**

```bash
uv run linkedin-watcher --setup
```

When prompted:
1. Enter your LinkedIn email
2. Browser will open
3. Sign in to LinkedIn
4. Session will be saved

---

## Phase 3: Odoo ERP Configuration 🏢

### Status: NEEDS INFO FROM YOU

**Please provide:**

1. **Your Odoo Instance URL:**
   - Example: `https://mycompany.odoo.com`
   - NOT: `https://your-company.odoo.com` (placeholder)

2. **Your Database Name:**
   - Example: `mycompany_prod`
   - NOT: `your_database` (placeholder)

**Then I'll update your .env file**

---

## Phase 4: Slack Integration 💬

### Status: NEEDS SETUP

**Steps to get Slack Bot Token:**

1. **Go to:** https://api.slack.com/apps

2. **Click:** "Create New App" → "From scratch"

3. **App Name:** AI Employee
   **Workspace:** Select your workspace

4. **Add Features:**
   - Go to "OAuth & Permissions"
   - Add these scopes under "Bot Token Scopes":
     - `channels:read`
     - `channels:history`
     - `chat:write`
     - `reactions:write`

5. **Install to Workspace:**
   - Click "Install to Workspace"
   - Copy the "Bot User OAuth Token" (starts with `xoxb-`)

6. **Get Webhook URL (optional):**
   - Go to "Incoming Webhooks"
   - Activate it
   - Add new webhook
   - Copy the URL

**Then I'll update your .env with the tokens**

---

## 📋 Quick Status Check

Run these commands to see what's done:

```bash
# Check Gmail token
stat -c "%y" secrets/gmail_token.json

# Check LinkedIn session  
ls -la secrets/linkedin_session/

# Check current Odoo config
grep ODOO_URL .env

# Check current Slack config
grep SLACK_BOT_TOKEN .env
```

---

## 🎯 Next Steps

**Complete in order:**

1. ✅ **Gmail** - Run `uv run gmail-watcher --setup` and complete auth
2. ✅ **LinkedIn** - Run `uv run linkedin-watcher --setup` and enter email
3. ✅ **Odoo** - Provide your Odoo URL and database name
4. ✅ **Slack** - Create app and get bot token

---

## 📞 Need Help?

For each phase, I can:
- Provide detailed step-by-step instructions
- Troubleshoot errors
- Test the integration after setup

**Just let me know which phase you're on!**
