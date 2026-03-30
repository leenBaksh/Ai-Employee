#!/bin/bash
# Restart WhatsApp webhook server with auto-reply enabled

cd /mnt/d/Hackathon-00/Ai-Employee

# Kill existing webhook processes
pkill -f whatsapp-webhook
pkill -f whatsapp_webhook_server
sleep 2

# Load .env and start webhook
export $(grep -v '^#' .env | xargs)
uv run whatsapp-webhook &

sleep 5

# Check health
echo "=== Webhook Server Status ==="
curl -s http://localhost:8089/health | python3 -m json.tool

echo ""
echo "✓ Webhook server restarted with auto-reply enabled"
