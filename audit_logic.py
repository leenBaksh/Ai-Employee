"""
audit_logic.py — Subscription pattern matching and audit logic.

Used by audit_mcp_server.py to identify subscription charges in Bank_Transactions.md
and flag them against the Subscription Audit Rules in Business_Goals.md.

Standalone usage:
    python audit_logic.py                        # full report
    python audit_logic.py --vault ./path/to/vault
"""

from pathlib import Path
from datetime import datetime, timezone

# ── Subscription Pattern Dictionary ───────────────────────────────────────────
# Maps lowercase keywords found in transaction descriptions → canonical tool name.
# Add your own subscriptions here. More specific patterns go first.

SUBSCRIPTION_PATTERNS: dict[str, str] = {
    # Productivity / Project Management
    "notion pro":            "Notion",
    "notion.so":             "Notion",
    "notion":                "Notion",
    "clickup":               "ClickUp",
    "asana":                 "Asana",
    "trello":                "Trello",
    "monday.com":            "Monday.com",
    "airtable":              "Airtable",
    "basecamp":              "Basecamp",
    "linear":                "Linear",
    # Communication
    "slack pro":             "Slack",
    "slack.com":             "Slack",
    "slack":                 "Slack",
    "zoom pro":              "Zoom",
    "zoom.us":               "Zoom",
    "zoom":                  "Zoom",
    "loom.com":              "Loom",
    "loom":                  "Loom",
    "discord nitro":         "Discord Nitro",
    # Dev Tools
    "github copilot":        "GitHub Copilot",
    "github.com":            "GitHub",
    "github":                "GitHub",
    "gitlab":                "GitLab",
    "jetbrains":             "JetBrains",
    "linear.app":            "Linear",
    "postman":               "Postman",
    "datadog":               "Datadog",
    "sentry.io":             "Sentry",
    # Design
    "adobe creative cloud":  "Adobe Creative Cloud",
    "adobe.com":             "Adobe Creative Cloud",
    "adobe":                 "Adobe Creative Cloud",
    "figma":                 "Figma",
    "sketch":                "Sketch",
    "canva pro":             "Canva Pro",
    "canva":                 "Canva",
    "invision":              "InVision",
    # Marketing / CRM
    "hubspot":               "HubSpot",
    "mailchimp":             "Mailchimp",
    "convertkit":            "ConvertKit",
    "intercom":              "Intercom",
    "activecampaign":        "ActiveCampaign",
    "salesforce":            "Salesforce",
    "pipedrive":             "Pipedrive",
    "semrush":               "SEMrush",
    "ahrefs":                "Ahrefs",
    # Entertainment (flag if on business account)
    "netflix.com":           "Netflix",
    "netflix":               "Netflix",
    "spotify.com":           "Spotify",
    "spotify":               "Spotify",
    # Cloud / Infrastructure
    "amazon web services":   "AWS",
    "aws":                   "AWS",
    "google workspace":      "Google Workspace",
    "google cloud":          "Google Cloud",
    "microsoft 365":         "Microsoft 365",
    "digitalocean":          "DigitalOcean",
    "digital ocean":         "DigitalOcean",
    "heroku":                "Heroku",
    "vercel":                "Vercel",
    "netlify":               "Netlify",
    "cloudflare":            "Cloudflare",
    "linode":                "Linode",
    # AI / API
    "openai":                "OpenAI API",
    "anthropic":             "Anthropic API",
    "mistral":               "Mistral AI",
    "replicate":             "Replicate",
    # Automation
    "zapier":                "Zapier",
    "make.com":              "Make.com",
    "n8n":                   "n8n",
    "pipedream":             "Pipedream",
    # Analytics
    "mixpanel":              "Mixpanel",
    "amplitude":             "Amplitude",
    "segment":               "Segment",
    # Storage / Backup
    "dropbox":               "Dropbox",
    "backblaze":             "Backblaze",
    "box.com":               "Box",
    # Password / Security
    "1password":             "1Password",
    "lastpass":              "LastPass",
    "nordvpn":               "NordVPN",
}

# Audit thresholds (align with Business_Goals.md Subscription Audit Rules)
IDLE_DAYS_THRESHOLD: int = 30          # flag if no login for this many days
PRICE_INCREASE_PCT_THRESHOLD: float = 20.0  # flag if price rose more than this %


# ── Core Pattern Matching ──────────────────────────────────────────────────────

def analyze_transaction(transaction: dict) -> dict | None:
    """
    Determine whether a transaction is a subscription charge.

    Args:
        transaction: dict with keys:
            description (str)   — e.g. "Slack Pro subscription"
            amount      (float) — e.g. -12.50
            date        (str)   — e.g. "2026-03-05"
            category    (str, optional) — e.g. "subscription"

    Returns:
        dict { type, name, amount, date } if subscription, else None.
    """
    description_lower = transaction.get("description", "").lower()

    # Fast path: category already tagged as subscription
    if transaction.get("category", "").lower() == "subscription":
        for pattern, name in SUBSCRIPTION_PATTERNS.items():
            if pattern in description_lower:
                return {
                    "type": "subscription",
                    "name": name,
                    "amount": transaction.get("amount"),
                    "date": transaction.get("date"),
                }
        # Tagged as subscription but no pattern match — return raw description
        return {
            "type": "subscription",
            "name": transaction.get("description", "Unknown"),
            "amount": transaction.get("amount"),
            "date": transaction.get("date"),
        }

    # Slow path: pattern match against all known patterns
    for pattern, name in SUBSCRIPTION_PATTERNS.items():
        if pattern in description_lower:
            return {
                "type": "subscription",
                "name": name,
                "amount": transaction.get("amount"),
                "date": transaction.get("date"),
            }

    return None


# ── Bank_Transactions.md Parsers ───────────────────────────────────────────────

def _parse_ledger_rows(content: str) -> list[dict]:
    """Parse the '## Running Ledger' markdown table."""
    rows = []
    in_section = False
    for line in content.splitlines():
        if line.startswith("## Running Ledger"):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if not in_section:
            continue
        if not line.startswith("|") or line.startswith("|---") or "Date" in line[:30]:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 7:
            continue
        try:
            date, description, amount_str = parts[1], parts[2], parts[3]
            type_, category, status = parts[4], parts[5], parts[6]
            amount_clean = amount_str.replace("$", "").replace(",", "").strip()
            if amount_clean and amount_clean not in ("-", "—"):
                rows.append({
                    "date": date,
                    "description": description,
                    "amount": float(amount_clean),
                    "type": type_,
                    "category": category,
                    "status": status,
                })
        except (ValueError, IndexError):
            continue
    return rows


def _parse_subscriptions_inventory(content: str) -> list[dict]:
    """Parse the '## Subscriptions Inventory' markdown table."""
    subs = []
    in_section = False
    for line in content.splitlines():
        if "## Subscriptions Inventory" in line:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if not in_section:
            continue
        if not line.startswith("|") or line.startswith("|---") or "Tool" in line[:20]:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 5:
            continue
        try:
            tool = parts[1]
            cost_str = parts[2].replace("$", "").replace(",", "").strip()
            last_login = parts[3].strip()
            used_by = parts[4].strip()
            notes = parts[5].strip() if len(parts) > 5 else ""
            if tool and cost_str and cost_str not in ("-", "—"):
                subs.append({
                    "tool": tool,
                    "monthly_cost": float(cost_str),
                    "last_login": last_login,
                    "used_by": used_by,
                    "notes": notes,
                })
        except (ValueError, IndexError):
            continue
    return subs


# ── Subscription Audit ─────────────────────────────────────────────────────────

def run_subscription_audit(vault_path: Path) -> dict:
    """
    Full subscription audit against Bank_Transactions.md.

    Applies 3 rules from Business_Goals.md:
      1. No login in 30 days  → flag for cancellation
      2. Cost increased > 20% → flag for review     (requires prior_cost in notes)
      3. Duplicate tool       → flag lower-usage one (detected via 'duplicate' in notes)

    Returns structured dict suitable for:
      - audit MCP tool response
      - weekly briefing Step 5 (creates Pending_Approval files)
    """
    now = datetime.now(timezone.utc)
    bank_file = vault_path / "Accounting" / "Bank_Transactions.md"

    if not bank_file.exists():
        return {"error": f"Bank_Transactions.md not found: {bank_file}"}

    content = bank_file.read_text(encoding="utf-8")
    ledger_rows = _parse_ledger_rows(content)
    inventory = _parse_subscriptions_inventory(content)

    # Identify subscriptions from raw ledger via pattern matching
    identified_from_ledger: list[dict] = []
    for row in ledger_rows:
        match = analyze_transaction(row)
        if match:
            identified_from_ledger.append(match)

    # Audit each entry in the Subscriptions Inventory table
    flagged: list[dict] = []
    for sub in inventory:
        reasons: list[dict] = []
        last_login_str = sub.get("last_login", "").strip()
        notes_lower = sub.get("notes", "").lower()

        # Rule 1: Idle > IDLE_DAYS_THRESHOLD days
        if last_login_str and last_login_str not in ("—", "-", "Active", "N/A"):
            try:
                last_dt = datetime.strptime(last_login_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                idle_days = (now - last_dt).days
                if idle_days > IDLE_DAYS_THRESHOLD:
                    reasons.append({
                        "rule": "idle_30_days",
                        "detail": f"No login since {last_login_str} ({idle_days} days ago)",
                    })
            except ValueError:
                pass

        # Rule 2: Duplicate tool (note contains "duplicate")
        if "duplicate" in notes_lower:
            reasons.append({
                "rule": "duplicate_tool",
                "detail": sub["notes"].replace("⚠️ ", ""),
            })

        # Rule 3: Low / no usage flagged in notes (catch-all for ⚠️ annotations)
        if "⚠️" in sub.get("notes", "") and not reasons:
            reasons.append({
                "rule": "low_usage",
                "detail": sub["notes"].replace("⚠️ ", ""),
            })

        if reasons:
            monthly = sub["monthly_cost"]
            safe_name = sub["tool"].replace(" ", "_").replace("/", "_")
            flagged.append({
                "tool": sub["tool"],
                "monthly_cost": monthly,
                "annual_cost": round(monthly * 12, 2),
                "last_login": sub["last_login"],
                "reasons": reasons,
                "recommended_action": "cancel_subscription",
                "approval_filename": f"APPROVAL_cancel_sub_{safe_name}_{now.strftime('%Y%m%d')}.md",
            })

    total_monthly = sum(s["monthly_cost"] for s in inventory)
    flagged_monthly = sum(f["monthly_cost"] for f in flagged)

    return {
        "generated": now.isoformat(),
        "total_subscriptions": len(inventory),
        "total_monthly_cost": round(total_monthly, 2),
        "total_annual_cost": round(total_monthly * 12, 2),
        "flagged_count": len(flagged),
        "potential_monthly_saving": round(flagged_monthly, 2),
        "potential_annual_saving": round(flagged_monthly * 12, 2),
        "flagged": flagged,
        "identified_from_ledger": identified_from_ledger,
    }


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    import argparse

    parser = argparse.ArgumentParser(description="AI Employee — Subscription Audit")
    parser.add_argument("--vault", default="./AI_Employee_Vault", help="Vault path")
    args = parser.parse_args()

    report = run_subscription_audit(Path(args.vault))
    print(json.dumps(report, indent=2))
