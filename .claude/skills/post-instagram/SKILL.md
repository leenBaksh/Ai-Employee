# Skill: Post to Instagram

**Command:** `/post-instagram`
**Tier:** Gold
**MCP Required:** social, playwright

## Purpose
Draft an Instagram post, queue it for human approval, and publish it via Playwright MCP browser automation after approval. Handbook §4: never post without explicit human approval.

## When to Use
- User asks to "post on Instagram" or "share on Instagram"
- `/Scheduled/` contains a `TRIGGER_social_instagram_*.md` file
- User asks to review pending Instagram posts

## Steps

### Step 1 — Read Company Handbook
Read `AI_Employee_Vault/Company_Handbook.md`. Note social media rules.

### Step 2 — Check Daily Limits
Use social MCP: `social_check_limits("Instagram")`
- If limit reached: inform user, stop.

### Step 3 — Draft the Post
Use social MCP: `social_draft_post(platform="Instagram", content="...", media_url="")`
- Instagram posts ideally include a media_url (image/video)
- Content should include relevant hashtags

### Step 4 — Inform User
Tell the user:
- Draft at `To_Post/Instagram/`
- Approval file at `Pending_Approval/SOCIAL_INSTAGRAM_*.md`
- To approve: move approval file to `/Approved/`

### Step 5 — Wait for Approval
Monitor `/Approved/` for `SOCIAL_INSTAGRAM_*.md`.

### Step 6 — Orchestrator Creates Trigger
After approval, `/Scheduled/TRIGGER_social_instagram_*.md` is created.

### Step 7 — Publish via Playwright MCP
When a trigger file exists:
1. Start Playwright MCP server
2. Navigate to `https://www.instagram.com`
3. Log in using session at `secrets/instagram_session/` (if exists)
4. Click the "+" / Create button
5. Upload media (if media_url provided)
6. Enter caption/content
7. Apply filters if desired
8. Click Share
9. Screenshot confirmation
10. Log success and move files to `/Done/`

## Error Handling
- Login fails: create `Needs_Action/ALERT_instagram_login_failed.md`
- No media: Instagram may require an image — alert user
- Rate limit: log and skip

## Handbook Rules
- Max 2 Instagram posts per day
- Images must be appropriate and brand-consistent
- Hashtags should be relevant
