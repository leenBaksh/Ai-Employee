# Skill: Post to Twitter/X

**Command:** `/post-twitter`
**Tier:** Gold
**MCP Required:** social, playwright

## Purpose
Draft a Twitter/X post, queue it for human approval, and publish it via Playwright MCP browser automation after approval. Handbook §4: never post without explicit human approval.

## When to Use
- User asks to "tweet", "post on Twitter", or "share on X"
- `/Scheduled/` contains a `TRIGGER_social_twitter_*.md` file
- User asks to review pending Twitter posts

## Steps

### Step 1 — Read Company Handbook
Read `AI_Employee_Vault/Company_Handbook.md`. Note social media rules.

### Step 2 — Check Daily Limits
Use social MCP: `social_check_limits("Twitter")`
- Limit is 5 posts/day (configurable via TWITTER_MAX_POSTS_PER_DAY)

### Step 3 — Draft the Post
Use social MCP: `social_draft_post(platform="Twitter", content="...", media_url="")`
- Keep content under 280 characters for a single tweet
- Include relevant hashtags and mentions

### Step 4 — Inform User
Tell the user:
- Draft at `To_Post/Twitter/`
- Approval file at `Pending_Approval/SOCIAL_TWITTER_*.md`
- To approve: move approval file to `/Approved/`

### Step 5 — Wait for Approval
Monitor `/Approved/` for `SOCIAL_TWITTER_*.md`.

### Step 6 — Orchestrator Creates Trigger
After approval, `/Scheduled/TRIGGER_social_twitter_*.md` is created.

### Step 7 — Publish via Playwright MCP
When a trigger file exists:
1. Start Playwright MCP server
2. Navigate to `https://twitter.com/compose/tweet`
3. Log in using session at `secrets/twitter_session/` (if exists)
4. Type the tweet content in the compose box
5. Add media if media_url provided
6. Click Tweet/Post
7. Screenshot confirmation
8. Log success and move files to `/Done/`

## Error Handling
- Login fails: create `Needs_Action/ALERT_twitter_login_failed.md`
- Content > 280 chars: truncate or ask user to shorten
- Rate limited by Twitter API: log and notify

## Handbook Rules
- Max 5 Twitter posts per day
- No spam or repetitive content
- Engage authentically
