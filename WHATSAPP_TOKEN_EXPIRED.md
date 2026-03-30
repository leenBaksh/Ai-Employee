# WhatsApp Access Token Expired - How to Refresh

## Error
```
Error validating access token: Session has expired on Tuesday, 24-Mar-26 14:00:00 PDT
```

## Quick Fix - Get New Token

### Option 1: Meta Developer Portal (Recommended - Permanent Token)

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Select your app → WhatsApp → API Setup
3. Under "Generate access token", click **Generate token**
4. Copy the new token (starts with `EAA...`)
5. Update your `.env` file:
   ```bash
   WHATSAPP_ACCESS_TOKEN=EAA...your_new_token_here
   ```
6. Restart the webhook server:
   ```bash
   ps aux | grep whatsapp_webhook | grep -v grep | awk '{print $2}' | xargs kill
   # Orchestrator will auto-restart it
   ```

### Option 2: Graph API Explorer (Temporary - Expires in 24 hours)

1. Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your app
3. Under "Add Permission", select:
   - `whatsapp_business_messaging`
   - `whatsapp_business_management`
4. Click **Generate Access Token**
5. Copy the token and update `.env`

### Option 3: Exchange Short-lived Token for Long-lived Token

If you have a short-lived token, exchange it for a long-lived one:

```bash
# Replace YOUR_SHORT_TOKEN with your current token
curl -X GET "https://graph.facebook.com/v25.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=YOUR_SHORT_TOKEN"
```

## Verify Token Works

After updating the token, test it:

```bash
curl -s -X POST http://localhost:8089/test-send \
  -H "Content-Type: application/json" \
  -d '{"to": "923103871019", "message": "Test from AI Employee"}' | python3 -m json.tool
```

Expected response:
```json
{
  "success": true,
  "result": {
    "messages": [{"id": "wamid.xxx"}]
  }
}
```

## Why This Happens

- **Short-lived tokens**: Expire after 24 hours
- **Long-lived tokens**: Expire after 60 days
- **System user tokens**: Can be permanent (recommended for production)

For production use, create a **System User** in Meta Business Suite and generate a permanent token.
