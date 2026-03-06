#!/usr/bin/env python3
"""
Ralph Wiggum Stop Hook — keeps Claude looping until task is complete.

Reads Ralph state from {RALPH_STATE_DIR}/ralph_current.json.
Exit 0 = allow stop.
Exit 2 = block stop + re-inject continuation prompt.

Completion strategies (checked before circuit breaker):
  1. Promise-based: Claude outputs <promise>TASK_COMPLETE</promise> in transcript
  2. File-movement: source_file from state has moved to Done/

State file schema:
  {
    "active": true,
    "task": "description of what we're doing",
    "iterations": 3,
    "max_iterations": 10,
    "continuation_prompt": "Continue working on X. Next: do Y.",
    "source_file": "TASK_process_inbox_20260223.md",
    "started": "2026-02-23T08:00:00Z"
  }
"""
import os
import sys
import json
from pathlib import Path


PROMISE_TAG = "<promise>TASK_COMPLETE</promise>"


def _read_stdin_payload() -> dict:
    """Read JSON payload from stdin (Claude Code injects this for Stop hooks)."""
    try:
        raw = sys.stdin.read()
        if raw.strip():
            return json.loads(raw)
    except Exception:
        pass
    return {}


def _check_promise_in_transcript(payload: dict) -> bool:
    """Return True if recent assistant output contains the completion promise tag."""
    transcript_path = payload.get("transcript_path", "")
    if not transcript_path:
        return False
    try:
        lines = Path(transcript_path).read_text(encoding="utf-8").splitlines()
        # Scan last 50 transcript lines for the promise tag
        for line in reversed(lines[-50:]):
            try:
                entry = json.loads(line)
            except Exception:
                continue
            role = entry.get("role", "")
            content = entry.get("content", "")
            if role == "assistant":
                if isinstance(content, str) and PROMISE_TAG in content:
                    return True
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            text = block.get("text", "")
                            if PROMISE_TAG in text:
                                return True
    except Exception:
        pass
    return False


def _check_source_file_done(state: dict, vault_root: Path) -> bool:
    """Return True if state's source_file has moved to Done/."""
    source_file = state.get("source_file", "")
    if not source_file:
        return False
    done_dir = vault_root / "Done"
    # Check direct match and any subdirectory
    if (done_dir / source_file).exists():
        return True
    matches = list(done_dir.rglob(source_file))
    return bool(matches)


def _deactivate(state: dict, state_file: Path, reason: str) -> None:
    """Mark Ralph state as inactive and write back to disk."""
    state["active"] = False
    state["completed_reason"] = reason
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")


def main():
    state_dir = Path(os.getenv("RALPH_STATE_DIR", "./AI_Employee_Vault/Ralph_State"))
    vault_root = state_dir.parent  # AI_Employee_Vault/
    state_file = state_dir / "ralph_current.json"

    if not state_file.exists():
        # No active Ralph task — allow Claude to stop normally
        sys.exit(0)

    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except Exception as e:
        print(json.dumps({"decision": "allow", "reason": f"Could not read Ralph state: {e}"}))
        sys.exit(0)

    if not state.get("active", False):
        sys.exit(0)

    # ── Completion Strategy 1: Promise tag in transcript ──────────────────────
    payload = _read_stdin_payload()
    if _check_promise_in_transcript(payload):
        _deactivate(state, state_file, "promise_tag_detected")
        print(json.dumps({
            "decision": "allow",
            "reason": "Ralph loop: TASK_COMPLETE promise detected in output."
        }))
        sys.exit(0)

    # ── Completion Strategy 2: source_file moved to Done/ ────────────────────
    if _check_source_file_done(state, vault_root):
        _deactivate(state, state_file, "source_file_in_done")
        print(json.dumps({
            "decision": "allow",
            "reason": f"Ralph loop: source_file '{state.get('source_file')}' found in Done/."
        }))
        sys.exit(0)

    # ── Circuit breaker ───────────────────────────────────────────────────────
    iterations = state.get("iterations", 0)
    max_iterations = state.get("max_iterations", int(os.getenv("RALPH_MAX_ITERATIONS", "10")))

    if iterations >= max_iterations:
        _deactivate(state, state_file, "max_iterations_reached")
        state["expired"] = True
        state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        print(json.dumps({
            "decision": "allow",
            "reason": f"Ralph loop reached max iterations ({max_iterations}). Allowing stop."
        }))
        sys.exit(0)

    # ── Continue loop ─────────────────────────────────────────────────────────
    state["iterations"] = iterations + 1
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    continuation = state.get(
        "continuation_prompt",
        f"Continue working on the current task. This is iteration {iterations + 1}/{max_iterations}."
    )

    print(json.dumps({
        "decision": "block",
        "reason": f"Ralph loop active: iteration {iterations + 1}/{max_iterations} — task: {state.get('task', 'unknown')}",
        "continue_as": continuation
    }))
    sys.exit(2)


if __name__ == "__main__":
    main()
