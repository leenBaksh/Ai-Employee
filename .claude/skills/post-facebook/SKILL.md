# Skill: Post to Facebook

**Command:** `/post-facebook`
**Tier:** Gold
**MCP Required:** social, playwright

## Purpose
Draft a Facebook post, queue it for human approval, and publish it via Playwright MCP browser automation after approval. Handbook §4: never post without explicit human approval.

## When to Use
- User asks to "post on Facebook" or "share on Facebook"
- `/Scheduled/` contains a `TRIGGER_social_facebook_*.md` file
- User asks to review pending Facebook posts

## Steps

### Step 1 — Read Company Handbook
Read `AI_Employee_Vault/Company_Handbook.md`. Note social media rules.

### Step 2 — Check Daily Limits
Use social MCP: `social_check_limits("Facebook")`
- If limit reached: inform user, stop.

### Step 3 — Draft the Post
Use social MCP: `social_draft_post(platform="Facebook", content="...", media_url="")`
This saves the draft and creates a `/Pending_Approval/SOCIAL_FACEBOOK_*.md` file.

### Step 4 — Inform User
Tell the user:
- Draft created at `To_Post/Facebook/`
- Approval file at `Pending_Approval/`
- To approve: move the approval file to `/Approved/`

### Step 5 — Wait for Approval
Monitor `/Approved/` for `SOCIAL_FACEBOOK_*.md`. This is handled by the social watcher automatically.

### Step 6 — Orchestrator Creates Trigger
After approval, the orchestrator creates `/Scheduled/TRIGGER_social_facebook_*.md`.

### Step 7 — Publish via Playwright MCP
When a trigger file exists:
1. Start Playwright MCP server
2. Navigate to `https://www.facebook.com`
3. Log in using session at `secrets/facebook_session/` (if exists)
4. Click "What's on your mind?" / Create Post
5. Type the post content
6. Click Post/Publish
7. Screenshot confirmation
8. Log success to `/Logs/`
9. Move trigger and draft files to `/Done/`
10. Run `social_check_limits` and update Dashboard

## Error Handling
- Login fails: create `Needs_Action/ALERT_facebook_login_failed.md`
- Rate limit: log and skip, notify user
- Content error: log details, leave draft in place

## Handbook Rules
- Max 2 Facebook posts per day
- Always disclose AI involvement if asked
- No misleading claims
