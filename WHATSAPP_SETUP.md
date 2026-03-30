# WhatsApp Integration — AI Employee

Complete guide for setting up and troubleshooting WhatsApp integration.

## 📋 Overview

The AI Employee supports **two WhatsApp integration methods**:

| Method | Best For | Pros | Cons |
|--------|----------|------|------|
| **Meta Cloud API (Webhook)** | Production | ✅ Official API (ToS compliant)<br>✅ Real-time push notifications<br>✅ No browser needed<br>✅ Auto-reply support | ❌ Requires Meta Developer account<br>❌ Needs public URL for webhook |
| **WhatsApp Web Automation** | Testing/Local | ✅ No API setup<br>✅ Works with personal number<br>✅ Immediate local testing | ❌ Browser automation required<br>❌ Session may expire<br>❌ Polling-based (not real-time) |

**Recommended:** Use **Meta Cloud API** for production, WhatsApp Web for local testing.

---

## 🚀 Quick Start

### Option A: Meta Cloud API (Recommended)

```bash
# 1. Run diagnostics
uv run whatsapp-setup

# 2. Configure .env (see Setup Guide below)
# WHATSAPP_VERIFY_TOKEN=your_verify_token
# WHATSAPP_ACCESS_TOKEN=your_access_token
# WHATSAPP_PHONE_NUMBER_ID=your_phone_id

# 3. Test credentials
uv run whatsapp-setup

# 4. Start webhook server
uv run whatsapp-webhook

# 5. Set webhook URL in Meta Developer Portal
# https://your-domain.com/webhook

# 6. Start orchestrator
uv run orchestrator
```

### Option B: WhatsApp Web Automation

```bash
# 1. Login to WhatsApp Web (one-time)
uv run whatsapp-watcher --setup

# 2. Start watcher
uv run whatsapp-watcher

# 3. Or start full orchestrator
uv run orchestrator
```

---

## 📖 Setup Guide: Meta Cloud API

### Step 1: Create Meta Developer App

1. Go to [https://developers.facebook.com/apps](https://developers.facebook.com/apps)
2. Click **Create App** → Select **Other** → **Business**
3. Fill in app details and create

### Step 2: Add WhatsApp Product

1. In your app dashboard, click **Add Product** → **WhatsApp**
2. Go to **WhatsApp → API Setup**

### Step 3: Get Credentials

#### 3.1 Access Token
- In **WhatsApp → API Setup**, find **Temporary Access Token**
- Click **Copy** token
- For permanent token: Go to **Business Settings** → **Users** → **System Users**
  - Create system user with `whatsapp_business_messaging` permission
  - Generate access token

#### 3.2 Phone Number ID
- In **WhatsApp → API Setup**, find **Phone number ID**
- Copy the ID (looks like: `1032540726603479`)

#### 3.3 Verify Token
- Create your own verify token (any secure string)
- Example: `zvBzl3kylXukvXOEppu4TQG1WbM6je7E`

### Step 4: Configure .env

```bash
# WhatsApp Business Cloud API
WHATSAPP_VERIFY_TOKEN=your_verify_token_here
WHATSAPP_ACCESS_TOKEN=EAAa... (your permanent access token)
WHATSAPP_PHONE_NUMBER_ID=1032540726603479
WHATSAPP_WEBHOOK_PORT=8089
WHATSAPP_AUTO_REPLY=true
WHATSAPP_AUTO_REPLY_MESSAGE="Thanks for your message! Our AI Employee has received it and will follow up shortly."
```

### Step 5: Set Up Webhook

#### For Production (with public domain):

1. Deploy your app with the webhook server
2. In Meta Developer Portal: **WhatsApp → Configuration**
3. Set **Webhook URL**: `https://your-domain.com/webhook`
4. Set **Verify Token**: (same as in .env)
5. Subscribe to `messages` event

#### For Local Testing (with ngrok):

```bash
# 1. Install ngrok
# https://ngrok.com/download

# 2. Start webhook server
uv run whatsapp-webhook

# 3. In another terminal, start ngrok
ngrok http 8089

# 4. Copy the ngrok URL (e.g., https://abc123.ngrok.io)

# 5. In Meta Developer Portal, set:
# Webhook URL: https://abc123.ngrok.io/webhook
# Verify Token: (your WHATSAPP_VERIFY_TOKEN)
```

### Step 6: Test Integration

```bash
# Test webhook server
curl http://localhost:8089/health

# Expected response:
# {"status":"healthy","credentials_configured":true,...}

# Send test message (to yourself)
curl -X POST http://localhost:8089/test-send \
  -H "Content-Type: application/json" \
  -d '{"to":"+1234567890","message":"Test from AI Employee"}'
```

---

## 📖 Setup Guide: WhatsApp Web

### Step 1: Install Playwright

```bash
cd /mnt/d/Hackathon-00/Ai-Employee
uv add playwright
playwright install chromium
```

### Step 2: Login to WhatsApp Web

```bash
# This opens a browser window
uv run whatsapp-watcher --setup

# Scan the QR code with your phone:
# WhatsApp → Linked Devices → Link a Device
```

### Step 3: Start Watcher

```bash
# Normal mode (headless)
uv run whatsapp-watcher

# Or with visible browser for debugging
uv run whatsapp-watcher --no-headless
```

---

## 🔧 Troubleshooting

### Error: 401 Unauthorized

**Symptom:**
```
WhatsApp reply failed: Client error '401 Unauthorized'
for url 'https://graph.facebook.com/v25.0/.../messages'
```

**Causes:**
1. Access token expired
2. Wrong phone number ID
3. Token doesn't have required permissions

**Fix:**
```bash
# 1. Test token validity
curl -X GET "https://graph.facebook.com/v25.0/YOUR_PHONE_ID?fields=display_phone_number,quality_rating" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 2. If 401, generate new token:
# Go to https://developers.facebook.com/apps
# → Your App → WhatsApp → API Setup → Generate Token

# 3. Update .env with new token
```

### Error: QR Code Always Shows (WhatsApp Web)

**Symptom:** Session not saving, QR code appears every time

**Fix:**
```bash
# 1. Delete old session
rm -rf ./secrets/whatsapp_session

# 2. Re-login
uv run whatsapp-watcher --setup

# 3. Wait for full login before pressing Enter
# 4. Make sure to press Enter in terminal AFTER seeing chat list
```

### Error: Webhook Verification Failed

**Symptom:** Meta can't verify webhook URL

**Fix:**
1. Ensure webhook server is running: `uv run whatsapp-webhook`
2. Check URL is accessible: `curl http://localhost:8089/webhook?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=123`
3. For ngrok: ensure tunnel is active
4. Verify token matches exactly in .env and Meta Portal

### Error: Playwright Not Installed

```bash
# Install Playwright and browsers
uv add playwright
playwright install chromium
```

---

## 📊 Monitoring

### Check Webhook Status

```bash
# Health check
curl http://localhost:8089/health

# Statistics
curl http://localhost:8089/stats
```

### Check Messages Received

```bash
# Count messages in Needs_Action
ls -1 AI_Employee_Vault/Needs_Action/WHATSAPP_*.md | wc -l

# View recent messages
ls -lt AI_Employee_Vault/Needs_Action/WHATSAPP_*.md | head -5
```

### Check Orchestrator Logs

```bash
tail -f Logs/orchestrator.log | grep -i whatsapp
```

---

## 🎯 Usage Examples

### Receive Message → Create Task

1. Customer sends: "Hi, I need an invoice for last month"
2. Webhook receives message → creates `WHATSAPP_20260324T120000Z_Customer.md`
3. File saved to `AI_Employee_Vault/Needs_Action/`
4. Orchestrator detects new file → notifies Claude
5. Claude drafts reply → saves to `Pending_Approval/`
6. Human approves → moves to `Approved/`
7. Orchestrator sends reply via Cloud API

### Send Message (Outbound)

```python
# Via MCP tool (from Claude)
whatsapp_send_message(
    to="+1234567890",
    text="Your invoice is ready! Check your email."
)

# Creates approval file in Pending_Approval/
# After approval, orchestrator sends via Cloud API
```

---

## 📁 File Structure

```
AI_Employee/
├── watchers/
│   ├── whatsapp_watcher.py          # WhatsApp Web automation
│   └── whatsapp_webhook_server.py   # Cloud API webhook server
├── mcp_servers/
│   └── whatsapp_mcp_server.py       # MCP tools for Claude
├── scripts/
│   └── whatsapp_setup.py            # Setup & diagnostics
├── secrets/
│   └── whatsapp_session/            # Browser session (WhatsApp Web)
└── AI_Employee_Vault/
    ├── Needs_Action/
    │   └── WHATSAPP_*.md            # Received messages
    ├── Pending_Approval/
    │   └── APPROVAL_whatsapp_*.md   # Draft replies awaiting approval
    └── Logs/
        └── orchestrator.log         # Activity logs
```

---

## 🔐 Security Notes

1. **Never commit .env** — Contains API tokens
2. **Rotate tokens regularly** — Every 90 days recommended
3. **Use permanent tokens** — Temporary tokens expire in 24 hours
4. **Webhook verification** — Always verify incoming requests
5. **Rate limiting** — Max 5 WhatsApp messages per hour (configurable)

---

## 📞 Support

- **Documentation:** See `ARCHITECTURE.md` for system overview
- **Logs:** Check `Logs/orchestrator.log` for errors
- **Diagnostics:** Run `uv run whatsapp-setup` for full system check
- **Meta Developer Docs:** https://developers.facebook.com/docs/whatsapp/cloud-api

---

## ✅ Checklist

Before going to production:

- [ ] Meta Cloud API credentials configured in .env
- [ ] Access token tested and valid
- [ ] Webhook URL set in Meta Developer Portal
- [ ] Webhook server running (port 8089)
- [ ] Auto-reply message configured (optional)
- [ ] Rate limits set appropriately
- [ ] Test message sent and received successfully
- [ ] Backup: WhatsApp Web session saved (optional)

---

**Last Updated:** 2026-03-24  
**Version:** 1.0 (Dual-mode support)
