#!/usr/bin/env python3
"""
Ralph Wiggum Stop Hook — keeps Claude looping until task is complete.

Reads Ralph state from {RALPH_STATE_DIR}/ralph_current.json.
Exit 0 = allow stop.
Exit 2 = block stop + re-inject continuation prompt.

State file schema:
  {
    "active": true,
    "task": "description of what we're doing",
    "iterations": 3,
    "max_iterations": 10,
    "continuation_prompt": "Continue working on X. Next: do Y."
  }
"""
import os
import sys
import json
from pathlib import Path

def main():
    state_dir = Path(os.getenv("RALPH_STATE_DIR", "./AI_Employee_Vault/Ralph_State"))
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

    iterations = state.get("iterations", 0)
    max_iterations = state.get("max_iterations", int(os.getenv("RALPH_MAX_ITERATIONS", "10")))

    if iterations >= max_iterations:
        # Safety circuit breaker — don't loop forever
        print(json.dumps({
            "decision": "allow",
            "reason": f"Ralph loop reached max iterations ({max_iterations}). Allowing stop."
        }))
        # Mark task as expired
        state["active"] = False
        state["expired"] = True
        state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        sys.exit(0)

    # Increment iteration counter
    state["iterations"] = iterations + 1
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    continuation = state.get(
        "continuation_prompt",
        f"Continue working on the current task. This is iteration {iterations + 1}/{max_iterations}."
    )

    # Block stop — re-inject continuation prompt
    print(json.dumps({
        "decision": "block",
        "reason": f"Ralph loop active: iteration {iterations + 1}/{max_iterations} — task: {state.get('task', 'unknown')}",
        "continue_as": continuation
    }))
    sys.exit(2)


if __name__ == "__main__":
    main()
