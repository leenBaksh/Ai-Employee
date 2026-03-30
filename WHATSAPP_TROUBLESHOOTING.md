# WhatsApp Webhook Troubleshooting Guide

## Current Status

### ✅ What's Working
- Cloud API can send messages to your phone
- Webhook server is running and healthy
- Meta is sending webhooks to your server
- ngrok tunnel is active

### ❌ What's Not Working
- Meta is NOT sending message **text content** in webhooks
- Only sending: status updates (delivered, read) and contact info
- Task files not being created (no message text)
- Auto-reply not triggering (no message text)

---

## Webhook Payload Comparison

### What We're Getting (Current)
```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "id": "1307703427858135",
    "changes": [{
      "value": {
        "messaging_product": "whatsapp",
        "metadata": {
          "display_phone_number": "15551378016",
          "phone_number_id": "1032540726603479"
        },
        "contacts": [{
          "profile": {"name": "B A K S H I"},
          "wa_id": "923103871019"
        }]
      }
    }]
  }]
}
```

### What We Should Get (Expected)
```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "id": "1307703427858135",
    "changes": [{
      "value": {
        "messaging_product": "whatsapp",
        "metadata": {
          "display_phone_number": "15551378016",
          "phone_number_id": "1032540726603479"
        },
        "messages": [{
          "from": "923103871019",
          "id": "wamid.xxx",
          "type": "text",
          "text": {
            "body": "HELLO"
          },
          "timestamp": "1234567890"
        }]
      }
    }]
  }]
}
```

---

## Troubleshooting Steps

### Step 1: Verify Webhook Subscription

1. Go to: https://developers.facebook.com/apps
2. Select your WhatsApp app
3. Go to: **WhatsApp → Configuration**
4. Find: **"Webhook Fields"** or **"Subscribe to events"**

**Verify these are checked:**
- [ ] ✅ `messages` ← CRITICAL!
- [ ] ✅ `message_deliveries`
- [ ] ✅ `message_reads`

**If already checked:**
1. UNCHECK `messages`
2. Click **Save**
3. Wait 30 seconds
4. CHECK `messages` again
5. Click **Save**
6. Wait 60 seconds
7. Test again

---

### Step 2: Verify Test Phone Numbers

1. Go to: **WhatsApp → API Setup**
2. Find: **"Add a phone number"** or **"Test numbers"**
3. Verify your number is added: `+923103871019`
4. Verify recipient is added: `+1 (555) 137-8016`

**If not added:**
1. Click **"Add phone number"**
2. Enter your number
3. Verify with SMS code
4. Try again

---

### Step 3: Verify Webhook URL

1. Go to: **WhatsApp → Configuration**
2. Find: **Webhook** section
3. Click **Edit**

**Verify:**
```
Callback URL: https://cowedly-topline-sadye.ngrok-free.dev/webhook
Verify Token: zvBzl3kylXukvXOEppu4TQG1WbM6je7E
```

**Test:**
1. Click **"Verify"** button
2. Should show: **"Verified"** (green checkmark)
3. If fails, re-enter values and save

---

### Step 4: Use Meta Dashboard Test Feature

1. Go to: **WhatsApp → Configuration**
2. Find: **Webhook** section
3. Click **"Test"** or **"Send test notification"**
4. Select: `messages` event
5. Click **"Send"**

**Expected:**
- Dashboard shows: "Test webhook sent"
- Your logs show: POST with message content

---

### Step 5: Check App Publishing Status

**Current Status:** App is in **Development Mode** (unpublished)

**Implications:**
- ✅ Can test with registered phone numbers
- ✅ Can use dashboard test feature
- ❌ Cannot receive messages from unregistered numbers

**To receive from ANY number:**
1. Go to: **App Review → Publishing**
2. Click **"Publish App"**
3. Complete business verification
4. Wait for Meta approval

---

### Step 6: Check Rate Limits

Meta has rate limits for WhatsApp Business API:

**Free Tier (Test):**
- 1,000 conversations/month
- Limited to test numbers

**If limit exceeded:**
- Messages won't be delivered
- Wait until next month or upgrade

---

### Step 7: Check Phone Number Status

1. Go to: **WhatsApp → API Setup**
2. Find your phone number
3. Check status:

**Should show:**
- ✅ Green checkmark
- ✅ "Connected" or "Verified"

**If shows error:**
- Re-verify phone number
- Check SMS for verification code

---

## Quick Test Commands

### Test Webhook Server
```bash
curl http://localhost:8089/health
```

### Test Webhook Verification
```bash
curl "https://YOUR-NGROK-URL.ngrok-free.dev/webhook?hub.mode=subscribe&hub.verify_token=zvBzl3kylXukvXOEppu4TQG1WbM6je7E&hub.challenge=test"
```

### Check Logs
```bash
tail -100 /tmp/webhook.log | grep -A20 "POST"
```

### Check Stats
```bash
curl http://localhost:8089/stats
```

---

## Common Issues

### Issue 1: Only Status Updates, No Message Text
**Symptom:** Webhook shows `"statuses"` but no `"messages"`

**Cause:** `messages` event not properly subscribed

**Fix:** Re-subscribe to `messages` event (Step 1)

---

### Issue 2: Webhook Verification Fails
**Symptom:** Meta shows "Verification failed"

**Cause:** Verify token mismatch or URL unreachable

**Fix:**
1. Verify ngrok is running
2. Check token matches exactly
3. URL must end with `/webhook`

---

### Issue 3: Messages Not Delivered
**Symptom:** Can send but can't receive

**Cause:** Phone number not registered as test number

**Fix:** Add phone number in API Setup (Step 2)

---

### Issue 4: 401 Unauthorized
**Symptom:** API returns 401 error

**Cause:** Access token expired

**Fix:**
1. Go to: WhatsApp → API Setup
2. Generate new access token
3. Update .env file
4. Restart webhook server

---

## Current Configuration

| Setting | Value |
|---------|-------|
| ngrok URL | `https://cowedly-topline-sadye.ngrok-free.dev` |
| Webhook URL | `.../webhook` |
| Verify Token | `zvBzl3kylXukvXOEppu4TQG1WbM6je7E` |
| Phone Number ID | `1032540726603479` |
| Business Account ID | `1307703427858135` |
| Test Number | `+923103871019` |
| Recipient | `+1 (555) 137-8016` |

---

## Next Steps

1. **Complete Step 1** (Re-subscribe to messages event)
2. **Test with dashboard test feature** (Step 4)
3. **Send test message and reply**
4. **Check logs for message text**

---

## Contact Meta Support

If all steps fail:
1. Go to: https://developers.facebook.com/support
2. Submit ticket for WhatsApp Business API
3. Include webhook payload examples
4. Mention: "messages event not sending text content"

---

**Last Updated:** 2026-03-24 23:40 UTC
**Status:** Troubleshooting in progress
