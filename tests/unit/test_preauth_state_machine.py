"""AC-04 pre-auth lifecycle (app_spec §6.1)."""

import pytest

from src.domain.enums import PreAuthStatus as S
from src.domain.exceptions import InvalidPreAuthStateException
from src.domain.preauth_state_machine import ALLOWED_TRANSITIONS, OVERRIDE_TRANSITIONS, transition

ALL = list(S)


@pytest.mark.ac("AC-04")
@pytest.mark.parametrize("target", [S.APPROVED, S.PARTIALLY_APPROVED, S.REJECTED, S.QUERY_RAISED])
def test_ac04_pending_can_reach_every_outcome(target: S) -> None:
    assert transition(S.PENDING, target) is target


@pytest.mark.ac("AC-04")
def test_ac04_query_raised_returns_to_pending() -> None:
    assert transition(S.QUERY_RAISED, S.PENDING) is S.PENDING


@pytest.mark.ac("AC-04")
@pytest.mark.parametrize(
    ("src", "dst"), [(a, b) for a in ALL for b in ALL if b not in ALLOWED_TRANSITIONS.get(a, set())]
)
def test_ac04_disallowed_transitions_raise(src: S, dst: S) -> None:
    with pytest.raises(InvalidPreAuthStateException):
        transition(src, dst)


@pytest.mark.ac("AC-10")
def test_ac10_override_edges_only_from_rejected_or_query() -> None:
    assert set(OVERRIDE_TRANSITIONS) == {S.REJECTED, S.QUERY_RAISED}
    assert transition(S.REJECTED, S.APPROVED, override=True) is S.APPROVED
    assert transition(S.QUERY_RAISED, S.PARTIALLY_APPROVED, override=True) is S.PARTIALLY_APPROVED
    with pytest.raises(InvalidPreAuthStateException):
        transition(S.APPROVED, S.PARTIALLY_APPROVED, override=True)
    with pytest.raises(InvalidPreAuthStateException):
        transition(S.REJECTED, S.REJECTED, override=True)
