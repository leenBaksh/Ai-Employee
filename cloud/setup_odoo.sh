#!/usr/bin/env bash
# cloud/setup_odoo.sh — Deploy Odoo Community on Cloud VM (Platinum Tier)
#
# Installs: Odoo 17 Community (Docker), Nginx reverse proxy, Let's Encrypt HTTPS,
#           daily backup cron, and health monitoring integration.
#
# Tested on Ubuntu 22.04 LTS (Oracle Cloud Free Tier, AWS t2.micro).
#
# Usage:
#   export DOMAIN=odoo.yourdomain.com      # required
#   export ODOO_PASSWORD=changeme          # required — set a strong password
#   export EMAIL=admin@yourdomain.com      # for Let's Encrypt
#   bash cloud/setup_odoo.sh
#
# After install:
#   Odoo:  https://$DOMAIN
#   Admin: http://localhost:8069 (direct, behind firewall)

set -euo pipefail

# ── Variables ─────────────────────────────────────────────────────────────────

DOMAIN="${DOMAIN:-odoo.example.com}"
ODOO_PASSWORD="${ODOO_PASSWORD:-changeme}"
EMAIL="${EMAIL:-admin@example.com}"
ODOO_PORT=8069
BACKUP_DIR="/opt/odoo-backups"
ODOO_DATA_DIR="/opt/odoo-data"
INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Odoo Community Cloud Setup (Platinum Tier) ==="
echo "Domain:  $DOMAIN"
echo "Email:   $EMAIL"
echo "Backups: $BACKUP_DIR"
echo ""

# ── 1. System dependencies ────────────────────────────────────────────────────

echo "--- Installing Docker + Nginx + Certbot ---"
sudo apt-get update -qq
sudo apt-get install -y docker.io docker-compose-plugin nginx certbot python3-certbot-nginx curl

sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker "$(whoami)"

# ── 2. Odoo data directories ──────────────────────────────────────────────────

echo "--- Creating Odoo data directories ---"
sudo mkdir -p "$ODOO_DATA_DIR/addons" "$ODOO_DATA_DIR/config" "$BACKUP_DIR"
sudo chown -R "$(whoami):$(whoami)" "$ODOO_DATA_DIR" "$BACKUP_DIR"

# ── 3. Odoo config ────────────────────────────────────────────────────────────

cat > "$ODOO_DATA_DIR/config/odoo.conf" << EOF
[options]
addons_path = /mnt/extra-addons
data_dir = /var/lib/odoo
admin_passwd = ${ODOO_PASSWORD}
db_host = db
db_port = 5432
db_user = odoo
db_password = ${ODOO_PASSWORD}
workers = 2
max_cron_threads = 1
logfile = /var/log/odoo/odoo.log
log_level = warn
EOF

# ── 4. Docker Compose ─────────────────────────────────────────────────────────

echo "--- Writing docker-compose.yml ---"
cat > /opt/odoo-docker-compose.yml << EOF
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    restart: always
    environment:
      POSTGRES_USER: odoo
      POSTGRES_PASSWORD: ${ODOO_PASSWORD}
      POSTGRES_DB: odoo
    volumes:
      - odoo_db:/var/lib/postgresql/data

  odoo:
    image: odoo:17.0
    restart: always
    depends_on:
      - db
    ports:
      - "127.0.0.1:${ODOO_PORT}:8069"
    environment:
      HOST: db
      USER: odoo
      PASSWORD: ${ODOO_PASSWORD}
    volumes:
      - odoo_data:/var/lib/odoo
      - ${ODOO_DATA_DIR}/config:/etc/odoo
      - ${ODOO_DATA_DIR}/addons:/mnt/extra-addons

volumes:
  odoo_db:
  odoo_data:
EOF

# ── 5. Start Odoo ─────────────────────────────────────────────────────────────

echo "--- Starting Odoo + PostgreSQL ---"
sudo docker compose -f /opt/odoo-docker-compose.yml up -d
echo "Waiting 30s for Odoo to initialize..."
sleep 30

# ── 6. Nginx reverse proxy ────────────────────────────────────────────────────

echo "--- Configuring Nginx ---"
sudo tee /etc/nginx/sites-available/odoo > /dev/null << EOF
upstream odoo {
    server 127.0.0.1:${ODOO_PORT};
}

server {
    listen 80;
    server_name ${DOMAIN};

    # ACME challenge (Let's Encrypt)
    location /.well-known/acme-challenge/ { root /var/www/html; }

    location / {
        proxy_pass http://odoo;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 720s;
        proxy_connect_timeout 720s;
        proxy_send_timeout 720s;
        client_max_body_size 50m;
    }

    # Longpolling
    location /longpolling {
        proxy_pass http://127.0.0.1:8072;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/odoo /etc/nginx/sites-enabled/odoo
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# ── 7. HTTPS via Let's Encrypt ────────────────────────────────────────────────

echo "--- Obtaining Let's Encrypt certificate for $DOMAIN ---"
sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" || {
    echo "WARNING: Certbot failed (DNS not yet pointing to this server?)."
    echo "Re-run once DNS is set: sudo certbot --nginx -d $DOMAIN -m $EMAIL"
}

# ── 8. Daily backup cron ──────────────────────────────────────────────────────

echo "--- Setting up daily database backup ---"
BACKUP_SCRIPT="/usr/local/bin/odoo_backup.sh"
sudo tee "$BACKUP_SCRIPT" > /dev/null << 'BEOF'
#!/usr/bin/env bash
set -euo pipefail
BACKUP_DIR="/opt/odoo-backups"
DATE="$(date +%Y-%m-%d)"
DUMP="$BACKUP_DIR/odoo_$DATE.sql.gz"

docker exec "$(docker ps -qf name=odoo)" pg_dump -U odoo odoo | gzip > "$DUMP"
echo "Backup saved: $DUMP"

# Retain 30 days
find "$BACKUP_DIR" -name "odoo_*.sql.gz" -mtime +30 -delete
echo "Old backups pruned."
BEOF
sudo chmod +x "$BACKUP_SCRIPT"

CRON_BACKUP="0 2 * * * $BACKUP_SCRIPT >> /var/log/odoo_backup.log 2>&1"
( sudo crontab -l 2>/dev/null | grep -v odoo_backup.sh; echo "$CRON_BACKUP" ) | sudo crontab -
echo "Daily backup cron added (02:00 UTC)"

# ── 9. Health monitor integration ────────────────────────────────────────────

echo "--- Adding Odoo health check to vault ---"
HEALTH_SCRIPT="/usr/local/bin/odoo_health_check.sh"
sudo tee "$HEALTH_SCRIPT" > /dev/null << HEOF
#!/usr/bin/env bash
# Write Odoo health signal to vault for AI Employee health monitor
STATUS="offline"
HTTP_CODE=\$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://127.0.0.1:${ODOO_PORT}/web/health || echo "000")
[ "\$HTTP_CODE" = "200" ] && STATUS="online"

VAULT_PATH="${INSTALL_DIR}/AI_Employee_Vault"
mkdir -p "\$VAULT_PATH/Signals"
cat > "\$VAULT_PATH/Signals/HEALTH_odoo.json" << JSON
{
  "service": "odoo",
  "status": "\$STATUS",
  "http_code": "\$HTTP_CODE",
  "timestamp": "\$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "url": "https://${DOMAIN}"
}
JSON
HEOF
sudo chmod +x "$HEALTH_SCRIPT"

# Run health check every 5 minutes
CRON_HEALTH="*/5 * * * * $HEALTH_SCRIPT"
( sudo crontab -l 2>/dev/null | grep -v odoo_health_check; echo "$CRON_HEALTH" ) | sudo crontab -

# ── 10. Update .env for AI Employee Odoo MCP ─────────────────────────────────

echo ""
echo "--- Odoo MCP connection settings ---"
echo "Add these to your .env on the cloud VM:"
echo ""
echo "  ODOO_URL=https://${DOMAIN}"
echo "  ODOO_DB=odoo"
echo "  ODOO_USER=admin"
echo "  ODOO_PASSWORD=${ODOO_PASSWORD}"
echo ""

# ── Done ─────────────────────────────────────────────────────────────────────

echo "=== Odoo Setup Complete ==="
echo ""
echo "  Odoo URL:    https://${DOMAIN}"
echo "  Admin login: https://${DOMAIN}/web#action=login"
echo "  Backups:     $BACKUP_DIR (daily, 30-day retention)"
echo "  Logs:        journalctl + /var/log/odoo_backup.log"
echo ""
echo "Next steps:"
echo "  1. Open https://${DOMAIN} → complete Odoo first-run setup"
echo "  2. Add ODOO_* vars to .env and restart Cloud Agent"
echo "  3. Test: uv run python -c \"import mcp_servers.odoo_mcp_server\""
echo "  4. Health signal: cat AI_Employee_Vault/Signals/HEALTH_odoo.json"
