---
name: post-linkedin
description: |
  Draft and queue a LinkedIn post about business updates to generate sales leads.
  Writes the post to /To_Post/LinkedIn/ then creates an approval request.
  After human approval, uses the Playwright MCP to publish directly to LinkedIn.
  Use when the user asks to "post on LinkedIn", "share business update", or "generate a sales post".
  Also use when /Scheduled/ contains a TRIGGER_linkedin_post_*.md file.
  Handbook §5: approval required before posting. Max 2 posts/day.
---

# Post LinkedIn — AI Employee Skill

Draft a business LinkedIn post, queue it for approval, then publish via Playwright MCP after sign-off.

## Step 1: Read Rules

Read `AI_Employee_Vault/Company_Handbook.md` before acting.

Key rules for LinkedIn (§5 + LinkedIn Policy):
- Scheduled/pre-approved content → auto-allowed AFTER approval
- Immediate posts → ALWAYS require approval
- Max 2 posts per day
- Business updates only — never financial details publicly
- Never mention client names without consent

## Step 2: Gather Context

Read business context to craft a relevant post:

Read `AI_Employee_Vault/Business_Goals.md` and `AI_Employee_Vault/Dashboard.md`.

Check today's post count — read `AI_Employee_Vault/.linkedin_posts_today.json` if it exists.

If count >= 2: **STOP** — daily limit reached. Report to user.

## Step 3: Draft the Post

Write a compelling LinkedIn post following these guidelines:
- **Length:** 150–300 words (optimal LinkedIn engagement)
- **Hook:** Start with a strong first line (no "I am excited to announce")
- **Value:** Share insight, result, or lesson — not just promotion
- **CTA:** End with a soft call-to-action or question
- **Hashtags:** 3–5 relevant hashtags at the end
- **Tone:** Professional but human. First-person is fine.

Example formats that work well:
- Problem → Solution → Result story
- "3 things I learned from [project/client work]"
- Industry insight + your perspective
- Behind-the-scenes of your work process

## Step 4: Create Post File

Save to `AI_Employee_Vault/To_Post/LinkedIn/POST_<YYYY-MM-DD>_<slug>.md`:

```markdown
---
type: linkedin_post
created: <ISO timestamp>
status: pending_approval
topic: <brief topic description>
---

## Post Content

<The full LinkedIn post text here>

## Metadata
- Estimated reach: organic
- Hashtags: included in post
- Scheduled: awaiting approval
```

## Step 5: Create Approval Request

Create `AI_Employee_Vault/Pending_Approval/LINKEDIN_POST_<timestamp>.md`:

```markdown
---
type: linkedin_post
action: post_to_linkedin
created: <ISO timestamp>
expires: <+24 hours>
status: pending
post_file: To_Post/LinkedIn/POST_<name>.md
---

## LinkedIn Post Ready for Review

<Preview of the post content>

## To Approve
Move this file to /Approved/ — AI Employee will publish via Playwright MCP.

## To Reject
Move this file to /Rejected/
```

## Step 6: Watch for Approval

After creating the approval request, stop and wait. The orchestrator monitors `/Approved/`.

When the user moves the file to `/Approved/`, a trigger file will appear in `/Scheduled/`.
Proceed to Step 7 when `TRIGGER_linkedin_post_*.md` is detected.

## Step 7: Publish via Playwright MCP (after approval)

**Only run this step after the approval file has been moved to `/Approved/`.**

The Playwright MCP server runs at `http://localhost:8808`. Start it if needed:
```bash
bash .claude/skills/browsing-with-playwright/scripts/start-server.sh
python3 .claude/skills/browsing-with-playwright/scripts/verify.py
```

Use `mcp-client.py` to call `browser_*` tools:

### 7a. Navigate to LinkedIn feed
```bash
python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call \
  -u http://localhost:8808 -t browser_navigate \
  -p '{"url": "https://www.linkedin.com/feed/"}'
```
Take a screenshot to confirm login:
```bash
python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call \
  -u http://localhost:8808 -t browser_take_screenshot -p '{}'
```
If not logged in: stop and alert the user — they must log in first via the browser.

### 7b. Get page snapshot and open composer
```bash
python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call \
  -u http://localhost:8808 -t browser_snapshot -p '{}'
```
Find the "Start a post" button ref from the snapshot, then click it:
```bash
python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call \
  -u http://localhost:8808 -t browser_click \
  -p '{"element": "Start a post button", "ref": "<ref from snapshot>"}'
```

### 7c. Type the post content
Read the exact post content from `To_Post/LinkedIn/POST_<name>.md` (the `## Post Content` section).
Get a fresh snapshot, find the text editor ref, then type:
```bash
python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call \
  -u http://localhost:8808 -t browser_type \
  -p '{"element": "post editor", "ref": "<editor ref>", "text": "<full post content>"}'
```

### 7d. Submit the post
```bash
python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call \
  -u http://localhost:8808 -t browser_wait_for -p '{"time": 1000}'

python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call \
  -u http://localhost:8808 -t browser_click \
  -p '{"element": "Post button", "ref": "<post button ref>"}'
```
Wait 3 seconds, then take a screenshot to confirm the post was published.

### 7e. Update post count
Update `AI_Employee_Vault/.linkedin_posts_today.json`:
```json
{"date": "<today>", "count": <previous + 1>, "posts": [..., {"file": "<name>", "time": "<ISO>"}]}
```

### 7f. Archive and log
- Move the approved file from `/Approved/` to `/Done/`
- Move the trigger file from `/Scheduled/` to `/Done/`
- Log to `AI_Employee_Vault/Logs/<YYYY-MM-DD>.json`:
```json
{"timestamp": "<ISO>", "action_type": "linkedin_post", "actor": "claude_code", "target": "LinkedIn", "result": "success", "parameters": {"post_file": "<name>", "posts_today": <count>}}
```

## Step 8: Report

```
✅ LinkedIn post published via Playwright MCP
📋 Post file: To_Post/LinkedIn/POST_<name>.md
📊 Posts today: <count>/2
✅ Logged and archived
```

---

## If Called to Publish an Existing Approved Post

If the user says "post the approved LinkedIn post" or a trigger exists in `/Scheduled/TRIGGER_linkedin_post_*.md`:
1. Find the corresponding approved file in `/Approved/LINKEDIN_POST_*.md`
2. Read the `post_file:` frontmatter field to get the post content file
3. Read the post content from `To_Post/LinkedIn/POST_<name>.md`
4. Go directly to Step 7
