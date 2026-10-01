"""AC-08 cashless claim lifecycle (app_spec §6.2) — full 6x6 matrix."""

import pytest

from src.domain.claim_state_machine import ALLOWED_TRANSITIONS, ensure_case_mutable, transition
from src.domain.enums import CaseStatus as C
from src.domain.exceptions import ConflictError, InvalidClaimStateException

ALL = list(C)
SPEC_EDGES = {
    (C.PRE_AUTH, C.ADMITTED), (C.PRE_AUTH, C.CLOSED), (C.ADMITTED, C.DISCHARGED), (C.DISCHARGED, C.SETTLED),
    (C.DISCHARGED, C.DISPUTED), (C.DISPUTED, C.SETTLED), (C.DISPUTED, C.CLOSED), (C.SETTLED, C.CLOSED),
}


@pytest.mark.ac("AC-08")
def test_ac08_code_edges_match_spec_exactly() -> None:
    code_edges = {(a, b) for a, targets in ALLOWED_TRANSITIONS.items() for b in targets}
    assert code_edges == SPEC_EDGES


@pytest.mark.ac("AC-08")
@pytest.mark.parametrize(("src", "dst"), sorted(SPEC_EDGES))
def test_ac08_allowed_transitions(src: C, dst: C) -> None:
    assert transition(src, dst) is dst


@pytest.mark.ac("AC-08")
@pytest.mark.parametrize(("src", "dst"), [(a, b) for a in ALL for b in ALL if (a, b) not in SPEC_EDGES])
def test_ac08_4_every_disallowed_pair_raises(src: C, dst: C) -> None:
    with pytest.raises(InvalidClaimStateException) as err:
        transition(src, dst)
    assert err.value.code == "INVALID_CLAIM_STATE"


@pytest.mark.ac("AC-08")
def test_ac08_closed_is_terminal() -> None:
    assert ALLOWED_TRANSITIONS[C.CLOSED] == set()


@pytest.mark.nfr("NFR-08")
def test_settled_case_is_mutation_locked() -> None:
    with pytest.raises(ConflictError) as err:
        ensure_case_mutable(C.SETTLED)
    assert err.value.code == "CASE_SETTLED_IMMUTABLE"
    ensure_case_mutable(C.ADMITTED)
