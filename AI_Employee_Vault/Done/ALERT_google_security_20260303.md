---
type: alert
source: gmail
priority: high
status: pending
created: 2026-03-03T19:10:00Z
---

# ⚠️ Security Alert — Google Account Activity (wdigital085@gmail.com)

Two Google security emails were received. Please verify you recognise both actions:

## 1. New Passkey Added (2026-02-28)
**From:** Google <no-reply@accounts.google.com>
**Snippet:** "New passkey added to your account wdigital085@gmail.com. If you didn't add a passkey, someone might be using your account."

→ **Action required:** Confirm you added this passkey. If not, secure account immediately at myaccount.google.com.

---

## 2. App Password Created (2026-02-27)
**From:** Google <no-reply@accounts.google.com>
**Snippet:** "App password created to sign in to your account wdigital085@gmail.com. If you didn't generate this password for AI Employee, someone might be using your account."

→ **Likely legitimate** — this appears to be the SMTP app password created for the AI Employee email-sending integration. Verify at myaccount.google.com → Security → App passwords.

---

## 3. 2-Step Verification Turned On (2026-02-27)
**From:** Google <no-reply@accounts.google.com>
**Snippet:** "Your Google Account wdigital085@gmail.com is now protected with 2-Step Verification."

→ ✅ **Good** — no action needed, this is a security improvement.

---

*Per Company Handbook §6 and §8 — security events are flagged immediately. Move to /Done/ once verified.*

---

## 4. App Password Sign-In Removed (2026-03-03)
**From:** Google <no-reply@accounts.google.com>
**Snippet:** "App password used to sign in was removed wdigital085@gmail.com"

→ ✅ **Expected** — the old OAuth refresh token was revoked when 2-Step Verification was turned on (2026-02-27), causing the `invalid_grant` error. Re-authorized successfully on 2026-03-03 at 22:21 UTC. Gmail watcher is running again with a fresh token.

*Updated: 2026-03-03T22:25Z*
