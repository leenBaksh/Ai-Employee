#!/usr/bin/env python3
"""
Lockdown Mode - Security feature for AI Employee

Usage:
    uv run python scripts/lockdown_mode.py enable   # Enable lockdown
    uv run python scripts/lockdown_mode.py disable  # Disable lockdown
    uv run python scripts/lockdown_mode.py status   # Check status
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

VAULT = Path("/mnt/d/Hackathon-00/Ai-Employee/AI_Employee_Vault")
LOCKDOWN_FILE = VAULT / ".lockdown_mode"
LOGS_DIR = VAULT / "Logs"

def enable_lockdown(reason: str = "Manual activation"):
    """Enable lockdown mode."""
    LOCKDOWN_FILE.write_text(f"""enabled: true
activated_at: {datetime.now(timezone.utc).isoformat()}
reason: {reason}
activated_by: admin
""", encoding="utf-8")
    
    _log("lockdown_enabled", reason)
    print("🔒 LOCKDOWN MODE ENABLED")
    print(f"   Reason: {reason}")
    print(f"   Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("\n⚠️  All incoming messages will be blocked until lockdown is disabled.")


def disable_lockdown():
    """Disable lockdown mode."""
    if LOCKDOWN_FILE.exists():
        LOCKDOWN_FILE.unlink()
    _log("lockdown_disabled", "Manual deactivation")
    print("✅ LOCKDOWN MODE DISABLED")
    print("   System returning to normal operation.")


def check_status():
    """Check lockdown status."""
    if LOCKDOWN_FILE.exists():
        content = LOCKDOWN_FILE.read_text(encoding="utf-8")
        print("🔒 LOCKDOWN MODE: ACTIVE")
        print("\nDetails:")
        for line in content.strip().split("\n"):
            print(f"   {line}")
    else:
        print("✅ LOCKDOWN MODE: INACTIVE")
        print("   System operating normally.")


def _log(action: str, details: str):
    """Log lockdown action."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
    
    import json
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action_type": action,
        "actor": "lockdown_mode",
        "target": "security",
        "parameters": {"details": details},
        "result": "success"
    }
    
    entries = []
    if log_file.exists():
        try:
            entries = json.loads(log_file.read_text(encoding="utf-8"))
        except:
            entries = []
    entries.append(entry)
    log_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("🔒 Lockdown Mode Tool")
        print("=" * 40)
        print("\nUsage:")
        print("  uv run python scripts/lockdown_mode.py enable [reason]")
        print("  uv run python scripts/lockdown_mode.py disable")
        print("  uv run python scripts/lockdown_mode.py status")
        sys.exit(1)
    
    action = sys.argv[1].lower()
    
    if action == "enable":
        reason = " ".join(sys.argv[2:]) or "Security precaution"
        enable_lockdown(reason)
    elif action == "disable":
        disable_lockdown()
    elif action == "status":
        check_status()
    else:
        print(f"❌ Unknown action: {action}")
        sys.exit(1)
