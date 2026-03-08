"""
retry_handler.py — §7.1/7.2 Error hierarchy + retry decorator for the AI Employee.

Error categories (§7.1):
  TransientError      — network timeout, rate limit → exponential backoff retry
  AuthenticationError — expired token, revoked access → alert human, pause ops
  LogicError          — misinterpretation, bad response → human review queue
  DataError           — corrupted file, missing field → quarantine + alert
  SystemError         — crash, disk full → watchdog + restart

Usage:
    from retry_handler import with_retry, with_retry_async, classify_error
    from retry_handler import TransientError, AuthenticationError, DataError

    @with_retry(max_attempts=3, base_delay=1, max_delay=60)
    def call_gmail_api(...):
        ...

    # Or classify a caught exception:
    try:
        response = requests.get(url, timeout=10)
    except Exception as e:
        raise classify_error(e) from e
"""

from __future__ import annotations

import time
import logging
from functools import wraps
from typing import Type

logger = logging.getLogger("retry_handler")


# ── §7.1 Error Hierarchy ───────────────────────────────────────────────────────

class AIEmployeeError(Exception):
    """Base class for all AI Employee typed errors."""
    category: str = "unknown"


class TransientError(AIEmployeeError):
    """Network timeout, API rate limit — safe to retry with exponential backoff."""
    category = "transient"


class AuthenticationError(AIEmployeeError):
    """Expired token, revoked access — alert human, pause operations immediately."""
    category = "authentication"


class LogicError(AIEmployeeError):
    """Claude misinterpretation, malformed response — route to human review queue."""
    category = "logic"


class DataError(AIEmployeeError):
    """Corrupted file, missing required field — quarantine the item and alert."""
    category = "data"


class SystemError(AIEmployeeError):
    """Orchestrator crash, disk full — watchdog restart required."""
    category = "system"


# ── Error classifier ───────────────────────────────────────────────────────────

# Strings that indicate a transient/retriable condition
_TRANSIENT = (
    "timeout", "timed out", "connection reset", "connection refused",
    "rate limit", "too many requests", "429", "503", "502", "504",
    "temporary", "retry", "connection error", "network", "ssl error",
    "read timeout", "remote end closed",
)

# Strings that indicate an authentication failure (do NOT retry)
_AUTH = (
    "401", "403", "unauthorized", "forbidden", "invalid_grant",
    "token expired", "token revoked", "access denied", "invalid credentials",
    "authentication failed", "invalid token", "unauthenticated",
)

# Strings that indicate data integrity problems
_DATA = (
    "json decode", "jsondecodeerror", "parse error", "invalid format",
    "missing field", "missing key", "corrupted", "malformed",
    "keyerror", "attributeerror", "typeerror: expected",
)

# Strings that indicate system-level failures
_SYSTEM = (
    "no space left", "disk full", "out of memory", "oom", "killed",
    "broken pipe", "errno 5", "input/output error",
)


def classify_error(exc: Exception) -> AIEmployeeError:
    """
    Classify a generic exception into the nearest AI Employee error category.

    Returns a wrapped AIEmployeeError subclass — call `raise classify_error(e) from e`
    so the original traceback is preserved.
    """
    if isinstance(exc, AIEmployeeError):
        return exc

    msg = str(exc).lower()
    exc_type = type(exc).__name__.lower()
    combined = f"{exc_type} {msg}"

    if any(p in combined for p in _SYSTEM):
        return SystemError(str(exc))
    if any(p in combined for p in _AUTH):
        return AuthenticationError(str(exc))
    if any(p in combined for p in _DATA):
        return DataError(str(exc))
    if any(p in combined for p in _TRANSIENT):
        return TransientError(str(exc))

    # Default: LogicError — unexpected but not clearly categorised
    return LogicError(str(exc))


# ── §7.2 Retry decorator (sync) ────────────────────────────────────────────────

def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable: tuple[Type[Exception], ...] = (TransientError,),
):
    """
    Decorator: retry on `retryable` exceptions with exponential backoff.

    Only TransientError is retried by default.
    AuthenticationError, DataError, LogicError, SystemError always bubble up immediately.

    Args:
        max_attempts: Total attempts including the first one.
        base_delay:   Seconds before first retry (doubles each attempt).
        max_delay:    Cap on the retry delay.
        retryable:    Exception types that trigger a retry.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retryable as e:
                    if attempt == max_attempts - 1:
                        raise
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(
                        f"[{func.__name__}] Attempt {attempt + 1}/{max_attempts} failed "
                        f"({type(e).__name__}): {e}. Retrying in {delay:.1f}s"
                    )
                    time.sleep(delay)
                except AIEmployeeError:
                    # Typed non-retryable error — propagate immediately
                    raise
                except Exception as e:
                    # Untyped exception — classify before deciding
                    classified = classify_error(e)
                    if isinstance(classified, retryable):
                        if attempt == max_attempts - 1:
                            raise classified from e
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(
                            f"[{func.__name__}] Attempt {attempt + 1}/{max_attempts} failed "
                            f"(classified as {classified.category}): {e}. Retrying in {delay:.1f}s"
                        )
                        time.sleep(delay)
                    else:
                        raise classified from e
        return wrapper
    return decorator


# ── §7.2 Retry decorator (async) ───────────────────────────────────────────────

def with_retry_async(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable: tuple[Type[Exception], ...] = (TransientError,),
):
    """Async version of with_retry — apply to `async def` functions."""
    import asyncio

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retryable as e:
                    if attempt == max_attempts - 1:
                        raise
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(
                        f"[{func.__name__}] Async attempt {attempt + 1}/{max_attempts} failed "
                        f"({type(e).__name__}): {e}. Retrying in {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                except AIEmployeeError:
                    raise
                except Exception as e:
                    classified = classify_error(e)
                    if isinstance(classified, retryable):
                        if attempt == max_attempts - 1:
                            raise classified from e
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(
                            f"[{func.__name__}] Async attempt {attempt + 1}/{max_attempts} failed "
                            f"(classified as {classified.category}): {e}. Retrying in {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise classified from e
        return wrapper
    return decorator


# ── CLI self-test ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    print("retry_handler — error classification test\n")

    test_exceptions = [
        ConnectionError("Connection refused: timeout after 10s"),
        PermissionError("HTTP 401 Unauthorized: invalid_grant"),
        ValueError("HTTP 403 Forbidden: token revoked"),
        KeyError("missing field 'amount' in transaction"),
        OSError("No space left on device"),
        RuntimeError("Claude returned unexpected JSON"),
        Exception("HTTP 429 Too Many Requests"),
        Exception("HTTP 503 Service Unavailable"),
    ]

    for exc in test_exceptions:
        classified = classify_error(exc)
        print(f"  {type(exc).__name__:20s} → {classified.category:15s} | {str(exc)[:60]}")

    print("\nRetry decorator test (3 attempts, instant backoff):")

    attempt_count = [0]

    @with_retry(max_attempts=3, base_delay=0.01, max_delay=0.1)
    def flaky_call():
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise TransientError(f"transient failure #{attempt_count[0]}")
        return "success on attempt 3"

    result = flaky_call()
    print(f"  Result: {result} (took {attempt_count[0]} attempts)")
