---
type: security_reminder
severity: medium
created: 2026-03-07T14:13:28.226389+00:00
status: pending
---

## Monthly Credential Rotation Reminder

Security policy requires credentials to be rotated monthly.

### Credentials to Rotate

- [ ] `GMAIL_CLIENT_SECRET` — regenerate in Google Cloud Console
- [ ] `SMTP_PASSWORD` — generate new Gmail App Password
- [ ] `BANK_API_TOKEN` — rotate in banking provider dashboard
- [ ] `WHATSAPP_ACCESS_TOKEN` — refresh Meta Business token
- [ ] `SLACK_BOT_TOKEN` — rotate in Slack app settings
- [ ] `DASHBOARD_PASSWORD` — update in dashboard-ui/.env.local
- [ ] `SESSION_SECRET` — regenerate random 64-char hex

### After Rotating

1. Update `.env` with new values
2. For Keychain storage: `python secrets_manager.py set <NAME> <new_value>`
3. Restart all watchers: `uv run python orchestrator.py`
4. Run `python secrets_manager.py scan` to verify no leaks in vault
5. Move this file to /Done/

### Verify No Leaks

```bash
python secrets_manager.py scan ./AI_Employee_Vault
```

---
*Handbook §6: rotate credentials monthly and after any suspected breach.*
