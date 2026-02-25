# AI Employee — Lessons Learned

**Tier:** Platinum (v0.4)
**Date:** 2026-02-26

A record of engineering decisions, debugging insights, and patterns discovered during development of the AI Employee system.

---

## 1. Windows / WSL Encoding Issues

**Problem:** Python scripts on Windows/WSL2 would fail with `UnicodeDecodeError` or produce garbled markdown when reading vault files.

**Root Cause:** Windows default encoding (`cp1252`) vs. UTF-8 mismatch. Python's `open()` uses the system locale by default.

**Fix:** Always specify `encoding='utf-8'` explicitly on every file read/write:
```python
# WRONG
with open(path) as f: content = f.read()

# RIGHT
content = path.read_text(encoding='utf-8')
path.write_text(content, encoding='utf-8')
```

**Lesson:** In a cross-platform project (WSL2 + Linux CI + potential Mac), always be explicit about encoding. Never rely on system defaults.

---

## 2. Virtual Environment Python Detection

**Problem:** When running `orchestrator.py` directly (not via `uv run`), child processes couldn't be started because `subprocess.Popen([sys.executable, ...])` pointed to the wrong Python binary.

**Root Cause:** `sys.executable` can point to the system Python, not the `.venv` Python, depending on how the script was invoked.

**Fix:** The `_find_venv_python()` method in orchestrator.py checks multiple locations:
```python
for candidate in [
    project_root / ".venv" / "Scripts" / "python.exe",  # Windows
    project_root / ".venv" / "bin" / "python",           # Linux/Mac
]:
    if candidate.exists():
        return str(candidate)
# Fall back to sys.executable if already in a venv
if sys.prefix != sys.base_prefix:
    return sys.executable
```

**Lesson:** Always use `uv run python orchestrator.py` to guarantee correct venv activation. The fallback detection is for resilience only.

---

## 3. MCP Stdio vs HTTP Transport

**Problem:** The plan initially suggested using Playwright MCP via HTTP (port 8808). This worked for testing but added complexity (start server, verify port, manage lifecycle).

**Discovery:** The standard `mcp` package uses stdio transport by default. All our custom MCP servers (`email`, `odoo`, `social`, `audit`) use stdio. Claude Code manages the process lifecycle automatically.

**Decision:** Email, Odoo, Social, and Audit MCP servers all use **stdio transport** (standard pattern). Playwright MCP uses HTTP because it's a third-party server (`npx @playwright/mcp@latest`) with its own transport.

**Pattern:**
```python
# Stdio MCP server (our servers)
async with stdio_server() as (read_stream, write_stream):
    await server.run(read_stream, write_stream, ...)

# HTTP MCP (Playwright — started separately)
# claude calls: python .claude/skills/.../mcp-client.py call -u http://localhost:8808 ...
```

**Lesson:** Use stdio for custom MCP servers — it's simpler, no port management, and Claude Code handles process lifecycle via `.claude/mcp.json`.

---

## 4. HITL Approval Pattern

**Problem:** Early designs had Claude directly calling external APIs (email send, LinkedIn post). This was powerful but unsafe — one hallucination could send an embarrassing email.

**Solution:** The vault-based HITL (Human-in-the-Loop) gate:
1. Claude writes to `/Pending_Approval/` (never to external services directly)
2. Human reviews and moves file to `/Approved/`
3. Orchestrator detects `/Approved/` file and executes via MCP
4. Result logged, file moved to `/Done/`

**Why it works:**
- Human sees the action before it happens
- Approval is an atomic filesystem operation (no race conditions)
- Rejected actions are preserved in `/Rejected/` for audit
- Natural "undo" — if Claude drafts something wrong, just delete the pending file

**Lesson:** For any action that affects the external world, use the Pending_Approval gate. The small delay (human review) is worth it for trust and safety.

---

## 5. Ralph Wiggum Stop Hook Mechanics

**Problem:** Complex multi-step tasks (process 10 inbox items, run audit, update dashboard) would stop partway because Claude naturally ends its response after completing a visible chunk of work.

**Solution:** The Claude Code Stop Hook mechanism:
1. Register hook in `.claude/settings.json` under `"Stop"`
2. Hook script runs every time Claude would stop
3. Hook reads `ralph_current.json` — if active, returns exit code 2
4. Exit code 2 tells Claude Code to re-inject the `continue_as` prompt
5. Claude continues working from where it left off

**Key insight:** The hook must be fast (< 1s) and stateless except for the JSON file. Heavy work (log analysis, vault scanning) should be done by Claude, not the hook.

**Safety circuit breaker:** `max_iterations` prevents infinite loops. Always set a reasonable limit (10-20 for batch tasks).

**Lesson:** The Stop Hook is a simple but powerful mechanism for autonomous batch processing. The state file approach means it survives Claude Code restarts.

---

## 6. Odoo JSON-RPC Authentication

**Problem:** Odoo's API has two distinct JSON-RPC endpoints:
- `/web/session/authenticate` — for login (gets `uid`)
- `/web/dataset/call_kw` — for all model operations

Many tutorials show the wrong endpoint structure.

**Working Pattern:**
```python
# Step 1: Authenticate
POST /web/session/authenticate
{
  "jsonrpc": "2.0", "method": "call",
  "params": {"db": DB, "login": USER, "password": PASS}
}
→ response.result.uid (integer, e.g., 2)

# Step 2: All operations use uid
POST /web/dataset/call_kw
{
  "jsonrpc": "2.0", "method": "call",
  "params": {
    "model": "res.partner",
    "method": "search_read",
    "args": [[["is_company", "=", True]]],
    "kwargs": {"fields": [...], "limit": 20}
  }
}
```

**Lesson:** Cache the `uid` per client instance. Odoo sessions are stateful — don't re-authenticate on every call if you can avoid it.

---

## 7. Social Media Rate Limiting

**Problem:** Multiple agents drafting posts simultaneously could exceed daily limits.

**Solution:** File-based daily counter in `.social_posts_today.json`:
```json
{"date": "2026-02-23", "posts": {"Facebook": 1, "Twitter": 2}}
```
- Reset when `date` changes
- Social MCP checks and enforces limits before creating drafts
- Human approval step provides an additional rate-limit checkpoint

**Lesson:** File-based counters are simpler than databases for single-process systems. The social_mcp_server.py is the single point of truth for daily counts.

---

## 8. Vault File Naming Conventions

Established conventions for vault files (enables pattern matching):

| Pattern | Type |
|---------|------|
| `EMAIL_*.md` | Email task from Gmail |
| `DRAFT_*.md` | Email draft for review |
| `LINKEDIN_POST_*.md` | LinkedIn post approval |
| `SOCIAL_{PLATFORM}_*.md` | Social post approval (Gold) |
| `INVOICE_*.md` | Invoice task |
| `PLAN_*.md` | Multi-step plan |
| `ALERT_*.md` | System alert |
| `TRIGGER_*.md` | Scheduled trigger for Claude |
| `RALPH_*.md` | Ralph Wiggum loop initiation |

**Lesson:** Consistent naming lets orchestrator code use simple `.glob()` patterns instead of parsing YAML frontmatter for routing. Much faster and more reliable.

---

## 9. Structured Logging Format

All actors (orchestrator, watchers, MCP servers) write to the same log format:
```json
{
  "timestamp": "2026-02-23T08:00:00Z",
  "action_type": "email_send",
  "actor": "email_mcp_server",
  "target": "client@example.com",
  "parameters": {"subject": "..."},
  "result": "success"
}
```

This enables the Audit MCP to:
- Search by actor (which component failed)
- Filter by result (find all errors)
- Count by action_type (what's most common)
- Sort by timestamp (recent first)

**Lesson:** Define the log schema early and stick to it. The Audit MCP only works because every log entry follows the same structure.

---

## 10. Claude Code Hook Paths Must Be Absolute

The Stop Hook (`python .claude/hooks/stop_hook.py`) ran from CWD=`AI_Employee_Vault/` instead of the project root — causing a `FileNotFoundError`. The fix was two-part:
1. Update `settings.json` to use an absolute path
2. Create a **shim** at `AI_Employee_Vault/.claude/hooks/stop_hook.py` that delegates to the real hook with the correct absolute `RALPH_STATE_DIR`

**Lesson:** Always use absolute paths in Claude Code hook commands. Claude Code appears to cache hook settings at session start — file changes only take effect in new sessions. A shim at the expected path is a pragmatic backup.

---

## 11. Playwright MCP Needs Shared Browser Context

Without `--shared-browser-context`, each Playwright MCP tool call opens a fresh browser context. Navigate + snapshot calls operate on different pages, making automation impossible.

**Fix:** Start Playwright MCP with:
```bash
npx @playwright/mcp@latest --port 8808 \
  --executable-path ~/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome \
  --headless \
  --shared-browser-context
```

**Lesson:** Always use `--shared-browser-context` for multi-step browser automation workflows. Also: Playwright MCP defaults to system Chrome — in headless servers use `--executable-path` to point at the bundled Chromium.

---

## 12. Distributed Agent Design: Claim-by-Move Is Atomic

File rename (move) operations are atomic at the filesystem level on Linux/macOS (single `rename()` syscall). Two processes cannot both successfully rename the same file — the second gets `FileNotFoundError`. This makes file-move a reliable mutex for distributed task claiming without needing a database or lock file.

**Pattern:**
```
Needs_Action/task.md → In_Progress/cloud/task.md  (atomic claim)
In_Progress/cloud/task.md → Done/task.md           (release after success)
In_Progress/cloud/task.md → Needs_Action/task.md   (release after failure)
```

**Lesson:** For a file-based distributed system, the filesystem IS the coordination layer. Use it.

---

## 13. Secrets Isolation in Distributed Systems

When syncing a vault between Cloud and Local agents via git, secrets (.env, tokens, credentials) must NEVER be included. The vault `.gitignore` is the enforcement mechanism — not trust or convention.

**Pattern:**
- Cloud Agent only reads from vault markdown (public data)
- Secrets live in `.env` on Local machine only
- Cloud Agent is **draft-only** — it never needs SMTP password, LinkedIn session, or banking credentials
- `.gitignore` in vault explicitly excludes: `.env`, `secrets/`, `*.json.bak`, `credentials.json`, `token.json`

**Lesson:** Design Cloud Agent with the minimum required permissions from the start. "Draft-only" is a security property, not a limitation.

---

## 14. Exponential Backoff Belongs in the Base Class

Gmail watcher had 7 DNS failures in 13 minutes on 2026-02-24. The watcher recovered automatically but had no backoff — it just retried every 60 seconds regardless.

**Fix:** Added exponential backoff to `BaseWatcher.run()`:
- 1st failure → wait `interval * 2`
- 2nd failure → wait `interval * 4`
- 3rd+ failure → wait `interval * 8`, write `ALERT_repeated_failure_*.md`
- Successful poll → reset counter to 0

**Lesson:** Put retry logic in the base class, not individual watchers. All watchers get it for free. The repeated-failure alert (Handbook §8) is critical for surfacing systemic issues to the human owner.
