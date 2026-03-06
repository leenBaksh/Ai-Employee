"""
rate_limiter.py — Action Rate Limiting for the AI Employee.

Prevents runaway automation by enforcing per-hour caps on outbound actions.
State is persisted to a JSON file so limits survive process restarts.

Default limits (all overridable via .env):
  Emails:           10/hour  (MAX_EMAILS_PER_HOUR)
  WhatsApp:          5/hour  (MAX_WHATSAPP_PER_HOUR)
  LinkedIn posts:    2/day   (LINKEDIN_MAX_POSTS_PER_DAY — existing)
  Social posts:      3/hour  (MAX_SOCIAL_POSTS_PER_HOUR)
  Odoo writes:       5/hour  (MAX_ODOO_WRITES_PER_HOUR)
  Banking writes:    3/hour  (MAX_BANKING_WRITES_PER_HOUR)
  Approvals granted: 20/hour (MAX_APPROVALS_PER_HOUR)

Usage:
    from rate_limiter import RateLimiter, RateLimitExceededError

    limiter = RateLimiter(vault_path=Path("./AI_Employee_Vault"))

    # Check before acting (raises on breach)
    limiter.check("email_send", max_per_hour=10)

    # Or use the guard context manager
    with limiter.guard("email_send", max_per_hour=10):
        send_email(...)

    # Check without raising
    allowed, used, limit = limiter.peek("email_send", max_per_hour=10)

    # Record after the fact (if you did the check separately)
    limiter.record("email_send")
"""

import os
import json
import logging
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("rate_limiter")

# ── Default limits (from env, with safe fallbacks) ────────────────────────────
LIMITS: dict[str, int] = {
    "email_send":        int(os.getenv("MAX_EMAILS_PER_HOUR",        "10")),
    "whatsapp_send":     int(os.getenv("MAX_WHATSAPP_PER_HOUR",       "5")),
    "social_post":       int(os.getenv("MAX_SOCIAL_POSTS_PER_HOUR",   "3")),
    "odoo_write":        int(os.getenv("MAX_ODOO_WRITES_PER_HOUR",    "5")),
    "banking_write":     int(os.getenv("MAX_BANKING_WRITES_PER_HOUR", "3")),
    "approval_granted":  int(os.getenv("MAX_APPROVALS_PER_HOUR",     "20")),
    "calendar_write":    int(os.getenv("MAX_CALENDAR_WRITES_PER_HOUR","5")),
}

WINDOW_SECONDS = 3600  # 1 hour rolling window


class RateLimitExceededError(Exception):
    """Raised when an action exceeds its per-hour limit."""
    def __init__(self, action: str, used: int, limit: int, reset_in: int):
        self.action    = action
        self.used      = used
        self.limit     = limit
        self.reset_in  = reset_in
        super().__init__(
            f"Rate limit exceeded for '{action}': {used}/{limit} actions in the last hour. "
            f"Resets in {reset_in // 60}m {reset_in % 60}s."
        )


class RateLimiter:
    """
    File-backed rolling-window rate limiter.

    State file: {vault_path}/Logs/.rate_limits.json
    Format: { "action_type": ["ISO timestamp", ...] }
    Timestamps older than WINDOW_SECONDS are pruned on each read.
    """

    def __init__(self, vault_path: Path):
        logs_dir = vault_path / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        self._state_file = logs_dir / ".rate_limits.json"

    # ── State I/O ──────────────────────────────────────────────────────────────

    def _load(self) -> dict[str, list[str]]:
        if not self._state_file.exists():
            return {}
        try:
            return json.loads(self._state_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self, state: dict) -> None:
        self._state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _prune(self, timestamps: list[str]) -> list[str]:
        """Remove timestamps older than the rolling window."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=WINDOW_SECONDS)
        return [ts for ts in timestamps if datetime.fromisoformat(ts) > cutoff]

    # ── Public API ─────────────────────────────────────────────────────────────

    def peek(self, action: str, max_per_hour: Optional[int] = None) -> tuple[bool, int, int]:
        """
        Check current usage without recording a new action.

        Returns:
            (allowed, used_in_window, limit)
        """
        limit = max_per_hour or LIMITS.get(action, 100)
        state = self._load()
        recent = self._prune(state.get(action, []))
        return len(recent) < limit, len(recent), limit

    def check(self, action: str, max_per_hour: Optional[int] = None) -> None:
        """
        Verify the action is within its rate limit AND record it.
        Raises RateLimitExceededError if the limit is exceeded.
        """
        limit  = max_per_hour or LIMITS.get(action, 100)
        state  = self._load()
        recent = self._prune(state.get(action, []))

        if len(recent) >= limit:
            # Calculate time until oldest event falls out of window
            oldest = min(datetime.fromisoformat(ts) for ts in recent)
            reset_at = oldest + timedelta(seconds=WINDOW_SECONDS)
            reset_in = max(0, int((reset_at - datetime.now(timezone.utc)).total_seconds()))
            raise RateLimitExceededError(action, len(recent), limit, reset_in)

        # Record this action
        recent.append(datetime.now(timezone.utc).isoformat())
        state[action] = recent
        self._save(state)
        logger.debug(f"Rate check OK: {action} {len(recent)}/{limit}")

    def record(self, action: str) -> None:
        """Record an action without checking the limit (use after external check)."""
        state  = self._load()
        recent = self._prune(state.get(action, []))
        recent.append(datetime.now(timezone.utc).isoformat())
        state[action] = recent
        self._save(state)

    @contextmanager
    def guard(self, action: str, max_per_hour: Optional[int] = None):
        """
        Context manager — checks and records the limit before running the block.

        Usage:
            with limiter.guard("email_send", max_per_hour=10):
                send_email(...)
        """
        self.check(action, max_per_hour)
        yield

    def status(self) -> dict:
        """Return current usage for all tracked action types."""
        state = self._load()
        result = {}
        for action, default_limit in LIMITS.items():
            recent = self._prune(state.get(action, []))
            result[action] = {
                "used":  len(recent),
                "limit": default_limit,
                "remaining": max(0, default_limit - len(recent)),
            }
        return result

    def reset(self, action: Optional[str] = None) -> None:
        """
        Clear rate limit state. Use for testing or emergency override.
        If action is None, clears all limits.
        """
        if action is None:
            self._state_file.write_text("{}", encoding="utf-8")
            logger.warning("All rate limits reset.")
        else:
            state = self._load()
            state.pop(action, None)
            self._save(state)
            logger.warning(f"Rate limit reset for '{action}'.")


# ── Module-level singleton (lazy-init) ────────────────────────────────────────
_default_limiter: Optional[RateLimiter] = None


def get_limiter(vault_path: Optional[Path] = None) -> RateLimiter:
    """Return the module-level limiter (creates if not yet initialised)."""
    global _default_limiter
    if _default_limiter is None:
        vp = vault_path or Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()
        _default_limiter = RateLimiter(vp)
    return _default_limiter


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    limiter = get_limiter()

    if len(sys.argv) > 1 and sys.argv[1] == "reset":
        action = sys.argv[2] if len(sys.argv) > 2 else None
        limiter.reset(action)
    else:
        status = limiter.status()
        print(f"{'Action':<25} {'Used':>6} {'Limit':>6} {'Remaining':>10}")
        print("-" * 52)
        for action, s in status.items():
            bar = "⚠️ " if s["remaining"] == 0 else "✅ " if s["used"] == 0 else "  "
            print(f"{bar}{action:<23} {s['used']:>6} {s['limit']:>6} {s['remaining']:>10}")
