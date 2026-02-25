#!/usr/bin/env python3
"""
Shim — delegates to the real stop_hook at the project root.
Claude Code runs hooks with CWD=AI_Employee_Vault, so this file bridges the gap.
"""
import os
import sys
import subprocess

real_hook = "/mnt/d/Hackathon-00/Ai-Employee/.claude/hooks/stop_hook.py"
state_dir = "/mnt/d/Hackathon-00/Ai-Employee/AI_Employee_Vault/Ralph_State"

env = {**os.environ, "RALPH_STATE_DIR": state_dir}
result = subprocess.run([sys.executable, real_hook], env=env)
sys.exit(result.returncode)
