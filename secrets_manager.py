"""
secrets_manager.py — Credential Management Abstraction Layer

Resolves secrets using a priority chain — stops at first match:
  1. Environment variable (fastest, works everywhere, CI-friendly)
  2. macOS Keychain via `keyring` library (if installed + on macOS)
  3. 1Password CLI via `op read` (if `op` binary is in PATH and signed in)
  4. Raises CredentialNotFoundError

This means you never need to change calling code when you upgrade your
secrets store — just stop exporting the env var and the next tier picks up.

Usage:
    from secrets_manager import get_secret, set_secret

    token = get_secret("GMAIL_CLIENT_SECRET")
    token = get_secret("BANK_API_TOKEN", required=False)  # returns None if missing

Setup:
    macOS Keychain:
        pip install keyring
        python secrets_manager.py set GMAIL_CLIENT_SECRET "your-value"

    1Password CLI:
        Install op: https://developer.1password.com/docs/cli/get-started/
        op signin
        # Store secrets as: op://AI Employee/<SECRET_NAME>/credential
        # e.g. op://AI Employee/GMAIL_CLIENT_SECRET/credential

    Environment variables (simplest):
        export GMAIL_CLIENT_SECRET="your-value"
        # or put in .env (never commit that file)
"""

import os
import sys
import subprocess
import logging
from typing import Optional

logger = logging.getLogger("secrets_manager")

# 1Password vault name (change to match your vault setup)
OP_VAULT = os.getenv("OP_VAULT_NAME", "AI Employee")
# Service name used for macOS Keychain entries
KEYCHAIN_SERVICE = "ai-employee"


class CredentialNotFoundError(Exception):
    """Raised when a required secret cannot be resolved from any source."""
    pass


# ── Resolution Chain ───────────────────────────────────────────────────────────

def _from_env(name: str) -> Optional[str]:
    """Check environment variables (includes values loaded from .env via dotenv)."""
    return os.environ.get(name)


def _from_keychain(name: str) -> Optional[str]:
    """Check macOS Keychain via the `keyring` library."""
    try:
        import keyring  # type: ignore
        value = keyring.get_password(KEYCHAIN_SERVICE, name)
        if value:
            logger.debug(f"Resolved '{name}' from macOS Keychain")
        return value
    except ImportError:
        return None
    except Exception:
        return None


def _from_1password(name: str) -> Optional[str]:
    """
    Resolve a secret from 1Password CLI.
    Expects the secret stored at: op://<OP_VAULT>/<name>/credential
    """
    try:
        result = subprocess.run(
            ["op", "read", f"op://{OP_VAULT}/{name}/credential"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            value = result.stdout.strip()
            if value:
                logger.debug(f"Resolved '{name}' from 1Password CLI")
                return value
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # `op` not installed or not responding
        pass
    except Exception:
        pass
    return None


def get_secret(name: str, required: bool = True) -> Optional[str]:
    """
    Resolve a secret by name using the priority chain:
      env var → macOS Keychain → 1Password CLI

    Args:
        name:     The credential name (e.g. "GMAIL_CLIENT_SECRET")
        required: If True, raises CredentialNotFoundError when not found.
                  If False, returns None silently.

    Returns:
        The secret value as a string, or None if not found and required=False.
    """
    for resolver in (_from_env, _from_keychain, _from_1password):
        value = resolver(name)
        if value is not None:
            return value

    if required:
        raise CredentialNotFoundError(
            f"Secret '{name}' not found in environment variables, "
            f"macOS Keychain (service='{KEYCHAIN_SERVICE}'), "
            f"or 1Password vault '{OP_VAULT}'.\n"
            f"  → Set it with: export {name}=your_value\n"
            f"  → Or store in Keychain: python secrets_manager.py set {name} <value>"
        )
    return None


def set_secret(name: str, value: str) -> bool:
    """
    Store a secret in macOS Keychain via the `keyring` library.
    Falls back to printing export instructions if keyring is unavailable.

    Returns True if stored in Keychain, False if only env instructions printed.
    """
    try:
        import keyring  # type: ignore
        keyring.set_password(KEYCHAIN_SERVICE, name, value)
        print(f"✅ Stored '{name}' in macOS Keychain (service='{KEYCHAIN_SERVICE}')")
        return True
    except ImportError:
        print(f"⚠️  keyring not installed. To store in Keychain: pip install keyring")
    except Exception as e:
        print(f"⚠️  Keychain write failed: {e}")

    print(f"Fallback: add to your .env file:\n  {name}={value[:4]}****")
    return False


def list_configured() -> dict:
    """
    Check which credentials are configured (without revealing values).
    Returns dict of {name: source} for all known AI Employee secrets.
    """
    known_secrets = [
        "GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET",
        "SMTP_USER", "SMTP_PASSWORD",
        "BANK_API_TOKEN",
        "WHATSAPP_VERIFY_TOKEN", "WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID",
        "SLACK_BOT_TOKEN",
        "ODOO_PASSWORD",
        "ANTHROPIC_API_KEY",
        "OPENROUTER_API_KEY",
        "DASHBOARD_PASSWORD", "SESSION_SECRET",
    ]

    report = {}
    for name in known_secrets:
        if os.environ.get(name):
            report[name] = "env"
        elif _from_keychain(name):
            report[name] = "keychain"
        elif _from_1password(name):
            report[name] = "1password"
        else:
            report[name] = "MISSING"
    return report


def scan_vault_for_leaks(vault_path: str = "./AI_Employee_Vault") -> list[dict]:
    """
    Scan vault markdown files for patterns that look like real credentials.
    Returns list of findings (file, line_number, pattern_matched).

    Patterns detected:
      - API key formats: sk-, ghp_, xoxb-, ya29., AIza, AKIA
      - Hex tokens > 32 chars
      - Passwords in YAML frontmatter: password: <value>
    """
    import re
    from pathlib import Path

    CREDENTIAL_PATTERNS = [
        (r"sk-[a-zA-Z0-9]{20,}", "OpenAI-style sk- key"),
        (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
        (r"xoxb-[0-9A-Za-z\-]+", "Slack Bot Token"),
        (r"ya29\.[a-zA-Z0-9_\-]+", "Google OAuth Access Token"),
        (r"AIza[0-9A-Za-z\-_]{35}", "Google API Key"),
        (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
        (r"[0-9a-f]{40,}", "Long hex token (possible secret)"),
        (r"password\s*:\s*(?!your_|<|placeholder|\*{4})[^\s\*<>]{6,}", "Plaintext password in YAML"),
        (r"api_key\s*=\s*['\"](?!your|<|placeholder)[^'\"]{8,}", "Hardcoded API key"),
    ]

    findings = []
    vault = Path(vault_path)
    for md_file in vault.rglob("*.md"):
        try:
            lines = md_file.read_text(encoding="utf-8", errors="ignore").splitlines()
            for lineno, line in enumerate(lines, 1):
                for pattern, label in CREDENTIAL_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        findings.append({
                            "file": str(md_file.relative_to(vault)),
                            "line": lineno,
                            "pattern": label,
                            "snippet": line.strip()[:80],
                        })
                        break  # one finding per line
        except Exception:
            continue
    return findings


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python secrets_manager.py get <NAME>          # resolve a secret")
        print("  python secrets_manager.py set <NAME> <VALUE>  # store in Keychain")
        print("  python secrets_manager.py list                # check all credentials")
        print("  python secrets_manager.py scan [vault_path]   # scan vault for leaks")
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "get" and len(sys.argv) >= 3:
        try:
            val = get_secret(sys.argv[2])
            print(f"{sys.argv[2]}={val[:4]}****")  # mask value
        except CredentialNotFoundError as e:
            print(f"❌ {e}")
            sys.exit(1)

    elif cmd == "set" and len(sys.argv) >= 4:
        set_secret(sys.argv[2], sys.argv[3])

    elif cmd == "list":
        status = list_configured()
        configured = {k: v for k, v in status.items() if v != "MISSING"}
        missing    = {k: v for k, v in status.items() if v == "MISSING"}
        print(f"✅ Configured ({len(configured)}):")
        for k, src in configured.items():
            print(f"   {k:35s} [{src}]")
        if missing:
            print(f"\n⚠️  Missing ({len(missing)}):")
            for k in missing:
                print(f"   {k}")

    elif cmd == "scan":
        vault = sys.argv[2] if len(sys.argv) > 2 else "./AI_Employee_Vault"
        findings = scan_vault_for_leaks(vault)
        if findings:
            print(f"⚠️  {len(findings)} potential credential leak(s) found:")
            for f in findings:
                print(f"  {f['file']}:{f['line']}  [{f['pattern']}]  {f['snippet']}")
        else:
            print("✅ No credential patterns detected in vault.")

    else:
        print(f"Unknown command: {sys.argv[1]}")
        sys.exit(1)
