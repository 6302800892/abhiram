"""AC-04 pre-auth lifecycle (app_spec §6.1). Override edges (AC-10) are separate and explicit."""

from __future__ import annotations

from src.domain.enums import PreAuthStatus as S
from src.domain.exceptions import InvalidPreAuthStateException

ALLOWED_TRANSITIONS: dict[S, set[S]] = {
    S.PENDING: {S.APPROVED, S.PARTIALLY_APPROVED, S.REJECTED, S.QUERY_RAISED},
    S.QUERY_RAISED: {S.PENDING},
    S.APPROVED: set(),
    S.PARTIALLY_APPROVED: set(),
    S.REJECTED: set(),
}

OVERRIDE_TRANSITIONS: dict[S, set[S]] = {
    S.REJECTED: {S.APPROVED, S.PARTIALLY_APPROVED},
    S.QUERY_RAISED: {S.APPROVED, S.PARTIALLY_APPROVED},
}

APPROVAL_STATUSES = frozenset({S.APPROVED, S.PARTIALLY_APPROVED})


def transition(current: S, target: S, *, override: bool = False) -> S:
    """Return `target` if the edge is allowed, else raise InvalidPreAuthStateException."""
    edges = OVERRIDE_TRANSITIONS if override else ALLOWED_TRANSITIONS
    if target not in edges.get(current, set()):
        raise InvalidPreAuthStateException(current.value, target.value)
    return target
