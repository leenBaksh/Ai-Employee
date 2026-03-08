"""
permission_guard.py — §6.4 Permission Boundaries for the AI Employee.

Enforces which actions are auto-approved vs. always require human approval.

Action categories and thresholds:
  email    → known contacts (single): auto | new contact / bulk / CC: approval
  payment  → known payee + recurring + <$50: auto | new payee / >$100: approval
  social   → scheduled posts/drafts: auto | replies / DMs / comments: approval
  file     → create / read inside vault: auto | delete / move outside vault: approval

Usage:
    from permission_guard import check, add_known_contact, add_known_payee

    result = check("email", vault_path, to="client@example.com")
    if result.requires_approval:
        # route to /Pending_Approval/
    else:
        # proceed directly, log with ApprovalStatus.AUTO

    # After a human-approved send, register the contact:
    add_known_contact("client@example.com", vault_path)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# ── Result type ────────────────────────────────────────────────────────────────

PermissionMode = Literal["auto", "approval"]


@dataclass
class PermissionResult:
    """Outcome of a permission check."""
    mode: PermissionMode   # "auto" = proceed | "approval" = needs human
    reason: str            # human-readable explanation
    category: str          # which rule category matched

    @property
    def requires_approval(self) -> bool:
        return self.mode == "approval"

    def __str__(self) -> str:
        icon = "✅ AUTO" if self.mode == "auto" else "🔒 APPROVAL REQUIRED"
        return f"{icon} [{self.category}] {self.reason}"


# ── Persistent state files ─────────────────────────────────────────────────────

_CONTACTS_FILE  = "Contacts/known_contacts.json"
_PAYEES_FILE    = "Accounting/known_payees.json"
_OPT_OUT_FILE   = "Contacts/opt_out_human_only.json"  # contacts who requested human-only comms

# Keywords that signal sensitive/high-risk context — always escalate to approval
_SENSITIVE_KEYWORDS = (
    # Emotional
    "condolence", "condolences", "sympathy", "bereavement", "grief", "sorry for your loss",
    "passed away", "deceased", "funeral",
    # Legal
    "contract", "legal", "attorney", "lawyer", "sue", "lawsuit", "litigation",
    "regulatory", "compliance", "gdpr", "subpoena", "arbitration",
    # Medical
    "medical", "diagnosis", "prescription", "treatment", "health condition",
    "disability", "insurance claim",
    # Conflict
    "conflict", "dispute", "complaint", "terminate", "termination", "fired",
    "harassment", "discriminat",
)

PAYMENT_AUTO_MAX    = 50.0    # USD — recurring payments below this are auto-approved
PAYMENT_HARD_MAX    = 100.0   # USD — above this ALWAYS requires approval


# ── Contacts helpers ───────────────────────────────────────────────────────────

def _load_known_contacts(vault_path: Path) -> set[str]:
    contacts_file = vault_path / _CONTACTS_FILE
    if not contacts_file.exists():
        return set()
    try:
        data = json.loads(contacts_file.read_text(encoding="utf-8"))
        return {c.lower().strip() for c in data.get("contacts", [])}
    except Exception:
        return set()


def _load_opt_out(vault_path: Path) -> set[str]:
    """Return emails of contacts who requested human-only communication."""
    opt_out_file = vault_path / _OPT_OUT_FILE
    if not opt_out_file.exists():
        return set()
    try:
        data = json.loads(opt_out_file.read_text(encoding="utf-8"))
        return {e.lower().strip() for e in data.get("opt_out", [])}
    except Exception:
        return set()


def add_opt_out(email: str, vault_path: Path) -> None:
    """Register a contact as requiring human-only communication (no AI-sent emails)."""
    opt_out_file = vault_path / _OPT_OUT_FILE
    opt_out_file.parent.mkdir(parents=True, exist_ok=True)
    entries: list[str] = []
    if opt_out_file.exists():
        try:
            entries = json.loads(opt_out_file.read_text(encoding="utf-8")).get("opt_out", [])
        except Exception:
            entries = []
    email = email.lower().strip()
    if email not in [e.lower() for e in entries]:
        entries.append(email)
        opt_out_file.write_text(
            json.dumps({"opt_out": sorted(entries),
                        "_note": "Contacts who requested human-only communication — AI must never auto-send to these addresses"},
                       indent=2),
            encoding="utf-8",
        )


def is_sensitive_content(text: str) -> str | None:
    """
    Scan text for sensitive keywords that require human review.
    Returns the matched keyword (for logging), or None if clean.
    Ethics principle: emotional, legal, medical, conflict contexts → always escalate.
    """
    lower = text.lower()
    for kw in _SENSITIVE_KEYWORDS:
        if kw in lower:
            return kw
    return None


def add_known_contact(email: str, vault_path: Path) -> None:
    """Register an email address as a known contact (call after human-approved send)."""
    contacts_file = vault_path / _CONTACTS_FILE
    contacts_file.parent.mkdir(parents=True, exist_ok=True)
    contacts: list[str] = []
    if contacts_file.exists():
        try:
            contacts = json.loads(contacts_file.read_text(encoding="utf-8")).get("contacts", [])
        except Exception:
            contacts = []
    email = email.lower().strip()
    if email not in [c.lower() for c in contacts]:
        contacts.append(email)
        contacts_file.write_text(
            json.dumps({"contacts": sorted(contacts)}, indent=2),
            encoding="utf-8",
        )


# ── Payees helpers ─────────────────────────────────────────────────────────────

def _load_known_payees(vault_path: Path) -> set[str]:
    payees_file = vault_path / _PAYEES_FILE
    if not payees_file.exists():
        return set()
    try:
        data = json.loads(payees_file.read_text(encoding="utf-8"))
        return {p.lower().strip() for p in data.get("payees", [])}
    except Exception:
        return set()


def add_known_payee(payee: str, vault_path: Path) -> None:
    """Register a payee as known (call after human-approved payment)."""
    payees_file = vault_path / _PAYEES_FILE
    payees_file.parent.mkdir(parents=True, exist_ok=True)
    payees: list[str] = []
    if payees_file.exists():
        try:
            payees = json.loads(payees_file.read_text(encoding="utf-8")).get("payees", [])
        except Exception:
            payees = []
    payee = payee.strip()
    if payee not in payees:
        payees.append(payee)
        payees_file.write_text(
            json.dumps({"payees": sorted(payees)}, indent=2),
            encoding="utf-8",
        )


# ── Rule: Email ────────────────────────────────────────────────────────────────

def check_email(
    to: str,
    vault_path: Path,
    bulk: bool = False,
    cc: str = "",
    subject: str = "",
    body: str = "",
) -> PermissionResult:
    """
    Auto-approve: reply to a single known contact, no CC, no sensitive content.
    Require approval: new contact, bulk, CC, opt-out recipient, or sensitive keywords.
    """
    recipients = [r.strip() for r in to.split(",") if r.strip()]

    # Opt-out check — contacts who requested human-only comms
    opt_out = _load_opt_out(vault_path)
    for addr in recipients:
        if addr.lower().strip() in opt_out:
            return PermissionResult(
                mode="approval",
                reason=f"{addr} has requested human-only communication — AI must not send autonomously",
                category="email",
            )

    # Sensitive content detection (subject + body)
    combined = f"{subject} {body}"
    matched_kw = is_sensitive_content(combined)
    if matched_kw:
        return PermissionResult(
            mode="approval",
            reason=f"sensitive context detected ('{matched_kw}') — emotional/legal/medical content requires human review",
            category="email",
        )

    if bulk or len(recipients) > 1:
        return PermissionResult(
            mode="approval",
            reason=f"bulk send to {len(recipients)} recipients — always requires approval",
            category="email",
        )
    if cc:
        return PermissionResult(
            mode="approval",
            reason="CC recipients present — always requires approval",
            category="email",
        )

    known = _load_known_contacts(vault_path)
    if to.lower().strip() in known:
        return PermissionResult(
            mode="auto",
            reason=f"{to} is a known contact",
            category="email",
        )

    return PermissionResult(
        mode="approval",
        reason=f"{to} is not a known contact — new contacts always require approval",
        category="email",
    )


# ── Rule: Payment ──────────────────────────────────────────────────────────────

def check_payment(
    amount: float,
    payee: str,
    vault_path: Path,
    recurring: bool = False,
) -> PermissionResult:
    """
    Auto-approve: recurring payment < $50 to a known payee.
    Require approval: new payee, or any amount > $100.
    """
    abs_amount = abs(amount)

    if abs_amount > PAYMENT_HARD_MAX:
        return PermissionResult(
            mode="approval",
            reason=f"${abs_amount:.2f} exceeds the ${PAYMENT_HARD_MAX:.0f} hard limit — always requires approval",
            category="payment",
        )

    known = _load_known_payees(vault_path)
    if payee.lower().strip() not in known:
        return PermissionResult(
            mode="approval",
            reason=f"'{payee}' is not a known payee — new payees always require approval",
            category="payment",
        )

    if recurring and abs_amount < PAYMENT_AUTO_MAX:
        return PermissionResult(
            mode="auto",
            reason=(
                f"recurring ${abs_amount:.2f} to known payee '{payee}' "
                f"is below the ${PAYMENT_AUTO_MAX:.0f} auto-approve threshold"
            ),
            category="payment",
        )

    return PermissionResult(
        mode="approval",
        reason=(
            f"${abs_amount:.2f} payment to '{payee}'"
            + (" (non-recurring)" if not recurring else "")
            + " — requires approval"
        ),
        category="payment",
    )


# ── Rule: Social Media ─────────────────────────────────────────────────────────

_SOCIAL_INTERACTIVE = {"reply", "dm", "direct_message", "comment", "mention"}
_SOCIAL_BROADCAST   = {"scheduled", "post", "draft", "story", "reel"}


def check_social(post_type: str) -> PermissionResult:
    """
    Auto-approve: scheduled posts and broadcast drafts.
    Require approval: replies, DMs, comments — any interactive engagement.
    """
    pt = post_type.lower().strip()

    if any(t in pt for t in _SOCIAL_INTERACTIVE):
        return PermissionResult(
            mode="approval",
            reason=f"social {post_type} (interactive engagement) — always requires approval",
            category="social",
        )

    if any(t in pt for t in _SOCIAL_BROADCAST):
        return PermissionResult(
            mode="auto",
            reason=f"{post_type} is a broadcast post within the daily limit — auto-approved",
            category="social",
        )

    # Unknown type — safe default
    return PermissionResult(
        mode="approval",
        reason=f"unknown post type '{post_type}' — defaulting to approval required",
        category="social",
    )


# ── Rule: File Operations ──────────────────────────────────────────────────────

_FILE_AUTO_OPS     = {"create", "read", "write", "list", "copy"}
_FILE_APPROVAL_OPS = {"delete", "unlink", "remove"}
_FILE_MOVE_OPS     = {"move", "rename"}


def check_file(
    operation: str,
    path: str,
    vault_path: Path,
) -> PermissionResult:
    """
    Auto-approve: create / read / write inside the vault.
    Require approval: any delete, or move/rename to a path outside the vault.
    """
    op = operation.lower().strip()
    target = Path(path).resolve()
    inside_vault = str(target).startswith(str(vault_path.resolve()))

    if op in _FILE_APPROVAL_OPS:
        return PermissionResult(
            mode="approval",
            reason=f"file delete ('{Path(path).name}') — always requires approval",
            category="file",
        )

    if op in _FILE_MOVE_OPS and not inside_vault:
        return PermissionResult(
            mode="approval",
            reason=f"file {op} to path outside vault ('{path}') — requires approval",
            category="file",
        )

    if op in _FILE_AUTO_OPS or (op in _FILE_MOVE_OPS and inside_vault):
        return PermissionResult(
            mode="auto",
            reason=f"file {op} inside vault — auto-approved",
            category="file",
        )

    return PermissionResult(
        mode="approval",
        reason=f"unknown file operation '{op}' — defaulting to approval required",
        category="file",
    )


# ── Unified interface ──────────────────────────────────────────────────────────

def check(
    category: Literal["email", "payment", "social", "file"],
    vault_path: Path,
    **kwargs,
) -> PermissionResult:
    """
    Unified permission check.

    Examples:
        check("email",   vault, to="client@example.com")
        check("email",   vault, to="client@example.com", subject="Sorry", body="condolences...")
        check("email",   vault, to="a@b.com,c@d.com", bulk=True)
        check("payment", vault, amount=-45.0, payee="AWS", recurring=True)
        check("payment", vault, amount=-150.0, payee="new-vendor")
        check("social",  vault, post_type="scheduled")
        check("social",  vault, post_type="reply")
        check("file",    vault, operation="delete", path="/vault/Done/task.md")
        check("file",    vault, operation="move",   path="/tmp/export.md")
    """
    if category == "email":
        return check_email(vault_path=vault_path, **kwargs)
    if category == "payment":
        return check_payment(vault_path=vault_path, **kwargs)
    if category == "social":
        return check_social(**kwargs)
    if category == "file":
        return check_file(vault_path=vault_path, **kwargs)
    return PermissionResult(
        mode="approval",
        reason=f"unknown category '{category}' — defaulting to approval required",
        category=category,
    )


# ── CLI — quick boundary test ──────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    vault = Path(os.getenv("VAULT_PATH", "./AI_Employee_Vault")).resolve()

    cases = [
        ("email",   {"to": "client@example.com"}),
        ("email",   {"to": "stranger@unknown.com"}),
        ("email",   {"to": "a@b.com,c@d.com"}),
        ("email",   {"to": "client@example.com", "cc": "boss@company.com"}),
        ("payment", {"amount": -30.0,  "payee": "AWS",        "recurring": True}),
        ("payment", {"amount": -30.0,  "payee": "new-vendor", "recurring": True}),
        ("payment", {"amount": -120.0, "payee": "AWS",        "recurring": True}),
        ("payment", {"amount": -80.0,  "payee": "AWS",        "recurring": False}),
        ("social",  {"post_type": "scheduled"}),
        ("social",  {"post_type": "reply"}),
        ("social",  {"post_type": "dm"}),
        ("file",    {"operation": "create", "path": str(vault / "Done/task.md")}),
        ("file",    {"operation": "delete", "path": str(vault / "Done/task.md")}),
        ("file",    {"operation": "move",   "path": str(vault / "Done/task.md")}),
        ("file",    {"operation": "move",   "path": "/tmp/export.md"}),
    ]

    print(f"Permission Boundaries — vault: {vault}\n")
    for cat, kwargs in cases:
        r = check(cat, vault, **kwargs)
        print(f"  {str(r)}")
        arg_str = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
        print(f"    → check({cat!r}, {arg_str})\n")
