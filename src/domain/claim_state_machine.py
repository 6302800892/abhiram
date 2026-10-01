"""AC-08 cashless claim lifecycle (app_spec §6.2) and the NFR-08 settled-case mutation lock."""

from __future__ import annotations

from src.domain.enums import CaseStatus as C
from src.domain.exceptions import ConflictError, InvalidClaimStateException

ALLOWED_TRANSITIONS: dict[C, set[C]] = {
    C.PRE_AUTH: {C.ADMITTED, C.CLOSED},
    C.ADMITTED: {C.DISCHARGED},
    C.DISCHARGED: {C.SETTLED, C.DISPUTED},
    C.DISPUTED: {C.SETTLED, C.CLOSED},
    C.SETTLED: {C.CLOSED},
    C.CLOSED: set(),
}


def transition(current: C, target: C) -> C:
    """Return `target` if allowed, else raise InvalidClaimStateException (409 INVALID_CLAIM_STATE)."""
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidClaimStateException(current.value, target.value)
    return target


def ensure_case_mutable(current: C) -> None:
    """NFR-08: once SETTLED, bills, procedures and settlements are frozen (only CLOSE remains)."""
    if current is C.SETTLED:
        raise ConflictError("CASE_SETTLED_IMMUTABLE", "case is settled; its bill, procedures and settlement are final")


def require_status(current: C, *allowed: C) -> None:
    """Guard for non-transition updates (procedures, bills): settled lock first, then state check."""
    ensure_case_mutable(current)
    if current not in allowed:
        raise InvalidClaimStateException(current.value, f"update allowed only in {[s.value for s in allowed]}")
