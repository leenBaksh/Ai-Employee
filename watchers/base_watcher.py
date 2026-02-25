"""base_watcher.py — Abstract base class for all AI Employee watchers."""

import time
import logging
import json
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)


class BaseWatcher(ABC):
    """
    Template for all AI Employee watchers.

    Subclasses implement check_for_updates() and create_action_file()
    to detect events and write them to the Obsidian vault.
    """

    def __init__(self, vault_path: str, check_interval: int = 60):
        self.vault_path = Path(vault_path).resolve()
        self.needs_action = self.vault_path / "Needs_Action"
        self.logs_path = self.vault_path / "Logs"
        self.check_interval = check_interval
        self.logger = logging.getLogger(self.__class__.__name__)
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Make sure required vault directories exist."""
        for folder in [self.needs_action, self.logs_path]:
            folder.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def check_for_updates(self) -> list:
        """Return a list of new items to process."""

    @abstractmethod
    def create_action_file(self, item) -> Path:
        """Create a .md file in Needs_Action and return its path."""

    def log_action(self, action_type: str, target: str, result: str, details: dict = None):
        """Append a structured JSON log entry to today's log file."""
        log_file = self.logs_path / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action_type": action_type,
            "actor": self.__class__.__name__,
            "target": target,
            "parameters": details or {},
            "result": result,
        }

        # Read existing entries or start fresh
        entries = []
        if log_file.exists():
            try:
                entries = json.loads(log_file.read_text(encoding='utf-8'))
            except json.JSONDecodeError:
                entries = []

        entries.append(entry)
        log_file.write_text(json.dumps(entries, indent=2), encoding='utf-8')

    def run(self):
        """Main event loop — runs continuously until interrupted.

        Uses exponential backoff on consecutive errors (Gold Tier §8 error handling):
          - 1st failure  → wait check_interval * 2
          - 2nd failure  → wait check_interval * 4
          - 3rd+ failure → wait check_interval * 8, write ALERT to /Needs_Action/
          - Reset on any successful poll.
        """
        self.logger.info(f"Starting {self.__class__.__name__} (interval={self.check_interval}s)")
        consecutive_errors = 0
        max_backoff = self.check_interval * 8

        while True:
            try:
                items = self.check_for_updates()
                # Successful poll — reset backoff counter
                if consecutive_errors > 0:
                    self.logger.info(f"Recovered after {consecutive_errors} consecutive error(s).")
                    consecutive_errors = 0
                for item in items:
                    try:
                        path = self.create_action_file(item)
                        self.logger.info(f"Created action file: {path.name}")
                        self.log_action("file_created", str(path), "success")
                    except Exception as e:
                        self.logger.error(f"Failed to create action file for {item}: {e}")
                        self.log_action("file_created", str(item), "error", {"error": str(e)})
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                self.logger.info(f"{self.__class__.__name__} stopped.")
                break

            except Exception as e:
                consecutive_errors += 1
                backoff = min(self.check_interval * (2 ** consecutive_errors), max_backoff)
                self.logger.error(
                    f"Error in check_for_updates (attempt {consecutive_errors}): {e}. "
                    f"Retrying in {backoff}s."
                )
                self.log_action(
                    "poll_error", self.__class__.__name__, "error",
                    {"error": str(e), "consecutive_errors": consecutive_errors, "backoff_seconds": backoff}
                )

                # Handbook §8: alert after 3 consecutive failures
                if consecutive_errors >= 3:
                    self._write_repeated_failure_alert(consecutive_errors, str(e))

                time.sleep(backoff)

    def _write_repeated_failure_alert(self, count: int, last_error: str):
        """Write an alert file to /Needs_Action/ after 3+ consecutive failures (Handbook §8)."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        alert_file = self.needs_action / f"ALERT_repeated_failure_{self.__class__.__name__}_{ts}.md"
        # Only create if no existing active alert for this watcher
        existing = list(self.needs_action.glob(f"ALERT_repeated_failure_{self.__class__.__name__}_*.md"))
        if existing:
            return
        content = f"""---
type: alert
severity: high
source: {self.__class__.__name__}
created: {datetime.now(timezone.utc).isoformat()}
consecutive_errors: {count}
---

## ⚠️ Repeated Failure Alert — {self.__class__.__name__}

**{self.__class__.__name__}** has failed **{count} consecutive times** and requires attention.

**Last error:** `{last_error}`

## Suggested Actions
- [ ] Check network connectivity and API credentials in `.env`
- [ ] Review recent log entries in `/Logs/`
- [ ] Restart the orchestrator if the issue persists

---
*Auto-generated by BaseWatcher exponential backoff handler · Handbook §8*
"""
        alert_file.write_text(content, encoding="utf-8")
        self.logger.warning(f"Wrote repeated-failure alert: {alert_file.name}")
