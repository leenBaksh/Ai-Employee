---
type: linkedin_trigger
approved_file: Approved/LINKEDIN_POST_20260304T095600Z.md
post_file: To_Post/LinkedIn/POST_2026-03-04_silver-tier-automation.md
created: 2026-03-04T16:56:51.945611+00:00
status: pending
---

# LinkedIn Post — Ready to Publish

An approved LinkedIn post is queued. Claude should run `/post-linkedin` to publish it
using the **Playwright MCP** browser tools.

## Approved File
`Approved/LINKEDIN_POST_20260304T095600Z.md`

## Post Content File
`To_Post/LinkedIn/POST_2026-03-04_silver-tier-automation.md`

## Instructions for Claude
1. Read the post content from `To_Post/LinkedIn/POST_2026-03-04_silver-tier-automation.md`
2. Navigate to https://www.linkedin.com/feed/ via Playwright MCP
3. Use browser tools to open the post composer, type the content, and submit
4. Archive this trigger to /Done/ after successful posting
5. Log the action to /Logs/

## Action
Run: `/post-linkedin` (Step 7 - publish approved post via Playwright MCP)
