"""
filesystem_watcher.py — Monitors the vault /Inbox folder for dropped files.

When a file appears in /Inbox, this watcher:
  1. Copies it to /Needs_Action/
  2. Creates a companion .md task file for Claude to process
  3. Logs the event

Usage:
    python -m watchers.filesystem_watcher
    # or via UV:
    uv run file-watcher
"""

import os
import shutil
import argparse
from pathlib import Path
from datetime import datetime, timezone
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from watchers.base_watcher import BaseWatcher


class InboxDropHandler(FileSystemEventHandler):
    """Watchdog event handler: reacts to files dropped into /Inbox."""

    def __init__(self, watcher: "FilesystemWatcher"):
        self.watcher = watcher

    def on_created(self, event):
        if event.is_directory:
            return
        source = Path(event.src_path)
        # Ignore hidden files and already-processed .md task files
        if source.name.startswith(".") or source.suffix == ".md":
            return
        self.watcher.logger.info(f"New file detected in Inbox: {source.name}")
        self.watcher.create_action_file(source)


class ActiveProjectDropHandler(FileSystemEventHandler):
    """Watchdog event handler: reacts to files dropped into /Active_Project."""

    def __init__(self, watcher: "FilesystemWatcher"):
        self.watcher = watcher

    def on_created(self, event):
        if event.is_directory:
            return
        source = Path(event.src_path)
        if source.name.startswith(".") or source.suffix == ".md":
            return
        self.watcher.logger.info(f"New project file detected in Active_Project: {source.name}")
        self.watcher.create_project_action_file(source)


class FilesystemWatcher(BaseWatcher):
    """
    Watches the Obsidian vault /Inbox folder using watchdog.

    This watcher uses event-driven detection instead of polling,
    so new files are picked up immediately (< 1 second latency).
    """

    def __init__(self, vault_path: str):
        super().__init__(vault_path, check_interval=0)  # event-driven, no polling interval
        self.inbox = self.vault_path / "Inbox"
        self.active_project = self.vault_path / "Active_Project"
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.active_project.mkdir(parents=True, exist_ok=True)
        self._observer = None

    def check_for_updates(self) -> list:
        # Not used — this watcher is event-driven via watchdog
        return []

    def create_action_file(self, source: Path) -> Path:
        """
        Copy the dropped file to /Needs_Action and create a .md task file.
        Returns the path to the created .md task file.
        """
        dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_name = source.stem.replace(" ", "_")

        # Destination paths
        dest_file = self.needs_action / f"FILE_{timestamp}_{source.name}"
        task_file = self.needs_action / f"TASK_{timestamp}_{safe_name}.md"

        if dry_run:
            self.logger.info(f"[DRY RUN] Would copy {source.name} → {dest_file.name}")
            self.logger.info(f"[DRY RUN] Would create task: {task_file.name}")
            return task_file

        # Copy the original file
        shutil.copy2(source, dest_file)
        self.logger.info(f"Copied: {source.name} → {dest_file.name}")

        # Create the .md task file for Claude
        task_file.write_text(
            f"""---
type: file_drop
source: inbox
original_name: {source.name}
file_ref: {dest_file.name}
size_bytes: {source.stat().st_size}
received: {datetime.now(timezone.utc).isoformat()}
priority: normal
status: pending
---

## File Dropped for Processing

A new file has been placed in the Inbox and is ready for your review.

**File:** `{source.name}`
**Size:** {source.stat().st_size:,} bytes
**Stored as:** `{dest_file.name}`

## Suggested Actions
- [ ] Review the file contents
- [ ] Determine required action (summarize / forward / archive)
- [ ] Move this task to `/Done/` when complete
- [ ] Update `Dashboard.md` with outcome

## Notes
_Add any observations or action taken here._
""",
            encoding='utf-8',
        )

        # Log the event
        self.log_action(
            action_type="inbox_file_detected",
            target=source.name,
            result="success",
            details={"task_file": task_file.name, "dest_file": dest_file.name},
        )

        return task_file

    def create_project_action_file(self, source: Path) -> Path:
        """
        Handle a file dropped into /Active_Project.
        Copies the file to /Needs_Action and creates a project-type task file.
        Returns the path to the created .md task file.
        """
        dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_name = source.stem.replace(" ", "_")

        dest_file = self.needs_action / f"PROJECT_{timestamp}_{source.name}"
        task_file = self.needs_action / f"PROJECT_TASK_{timestamp}_{safe_name}.md"

        if dry_run:
            self.logger.info(f"[DRY RUN] Would copy {source.name} → {dest_file.name}")
            self.logger.info(f"[DRY RUN] Would create project task: {task_file.name}")
            return task_file

        shutil.copy2(source, dest_file)
        self.logger.info(f"Copied project file: {source.name} → {dest_file.name}")

        # Infer project type from filename/extension for smarter defaults
        ext = source.suffix.lower()
        if ext in (".csv", ".xlsx", ".xls", ".ods"):
            project_hint = "This looks like a spreadsheet — likely financial data, transactions, or inventory."
            suggested_actions = (
                "- [ ] Parse and categorize rows (use pandas or read line by line)\n"
                "- [ ] Group by category/date and produce summary totals\n"
                "- [ ] Flag anomalies or missing values\n"
                "- [ ] Write summary report to /Plans/\n"
                "- [ ] Move this task to /Done/ when complete"
            )
        elif ext == ".pdf":
            project_hint = "This looks like a PDF document — likely a contract, invoice, or statement."
            suggested_actions = (
                "- [ ] Extract key fields (dates, amounts, parties, clauses)\n"
                "- [ ] Cross-reference with Odoo records if financial\n"
                "- [ ] Flag action items or deadlines\n"
                "- [ ] Write summary to /Plans/\n"
                "- [ ] Move this task to /Done/ when complete"
            )
        else:
            project_hint = "Review the file contents and determine the project scope."
            suggested_actions = (
                "- [ ] Read and understand the project requirements\n"
                "- [ ] Create a multi-step Plan.md in /Plans/\n"
                "- [ ] Identify approval requirements\n"
                "- [ ] Move this task to /Done/ when complete"
            )

        task_file.write_text(
            f"""---
type: project_drop
source: active_project
original_name: {source.name}
file_ref: {dest_file.name}
size_bytes: {source.stat().st_size}
received: {datetime.now(timezone.utc).isoformat()}
priority: high
status: pending
---

## Project File Dropped for Processing

A project file has been placed in Active_Project and requires a structured response.

**File:** `{source.name}`
**Size:** {source.stat().st_size:,} bytes
**Stored as:** `{dest_file.name}`

## Context

{project_hint}

## Suggested Actions

{suggested_actions}

## Notes
_Add project scope, dependencies, or constraints here._
""",
            encoding='utf-8',
        )

        self.log_action(
            action_type="project_file_detected",
            target=source.name,
            result="success",
            details={"task_file": task_file.name, "dest_file": dest_file.name},
        )

        return task_file

    def run(self):
        """Start the watchdog observer and block until interrupted."""
        self.logger.info(f"Watching inbox: {self.inbox}")
        self.logger.info(f"Watching active projects: {self.active_project}")
        self.logger.info("Drop a file into Inbox (quick tasks) or Active_Project (project work).")
        self.logger.info("Press Ctrl+C to stop.")

        self._observer = Observer()
        self._observer.schedule(InboxDropHandler(self), str(self.inbox), recursive=False)
        self._observer.schedule(ActiveProjectDropHandler(self), str(self.active_project), recursive=False)
        self._observer.start()

        try:
            while self._observer.is_alive():
                self._observer.join(timeout=1)
        except KeyboardInterrupt:
            self.logger.info("Stopping watcher...")
            self._observer.stop()
        finally:
            self._observer.join()
            self.logger.info("File System Watcher stopped.")


def main():
    parser = argparse.ArgumentParser(description="AI Employee — File System Watcher")
    parser.add_argument(
        "--vault",
        default=os.getenv("VAULT_PATH", "./AI_Employee_Vault"),
        help="Path to the Obsidian vault (default: ./AI_Employee_Vault or $VAULT_PATH)",
    )
    args = parser.parse_args()

    watcher = FilesystemWatcher(vault_path=args.vault)
    watcher.run()


if __name__ == "__main__":
    main()
