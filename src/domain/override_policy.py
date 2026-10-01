"""AC-10 / AD-R6: what an insurer admin may override. The role check itself lives at the controller."""

from __future__ import annotations

from src.domain.enums import SYSTEM_ACTOR, PreAuthStatus
from src.domain.exceptions import BusinessRuleError
from src.domain.preauth_state_machine import APPROVAL_STATUSES

MAX_REASON_LENGTH = 500


def is_overridable(current: PreAuthStatus, *, decided_by: str) -> bool:
    """Auto-rejected (REJECTED by SYSTEM) or escalated query (QUERY_RAISED, by anyone)."""
    if current is PreAuthStatus.REJECTED:
        return decided_by == SYSTEM_ACTOR
    return current is PreAuthStatus.QUERY_RAISED


def ensure_override_allowed(current: PreAuthStatus, *, decided_by: str, target: PreAuthStatus, reason: str) -> str:
    """Return the trimmed reason, or raise OVERRIDE_NOT_ALLOWED / OVERRIDE_REASON_REQUIRED (422)."""
    if not is_overridable(current, decided_by=decided_by):
        raise BusinessRuleError(
            "OVERRIDE_NOT_ALLOWED",
            "only an auto-rejected pre-auth or an escalated query can be overridden",
            {"current_status": current.value, "decided_by": decided_by},
        )
    if target not in APPROVAL_STATUSES:
        raise BusinessRuleError("OVERRIDE_NOT_ALLOWED", "an override must approve or partially approve")
    cleaned = reason.strip()
    if not cleaned:
        raise BusinessRuleError("OVERRIDE_REASON_REQUIRED", "an override reason is mandatory")
    if len(cleaned) > MAX_REASON_LENGTH:
        raise BusinessRuleError("OVERRIDE_REASON_REQUIRED", f"reason must be at most {MAX_REASON_LENGTH} characters")
    return cleaned
