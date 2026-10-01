---
name: claim-state-machine
description: Claim-case and pre-auth state machine reference for MediCard (AC-04, AC-08, AM-R1). Load before editing claim_state_machine.py, preauth_state_machine.py, case_service.py, or tests asserting InvalidClaimStateException.
---

# Claim State Machine

## Case transitions (app_spec §6.2)
```python
ALLOWED_TRANSITIONS = {
    CaseStatus.PRE_AUTH:   {CaseStatus.ADMITTED, CaseStatus.CLOSED},
    CaseStatus.ADMITTED:   {CaseStatus.DISCHARGED},
    CaseStatus.DISCHARGED: {CaseStatus.SETTLED, CaseStatus.DISPUTED},
    CaseStatus.DISPUTED:   {CaseStatus.SETTLED, CaseStatus.CLOSED},
    CaseStatus.SETTLED:    {CaseStatus.CLOSED},
    CaseStatus.CLOSED:     set(),
}
```
`transition(current, target)` returns `target` or raises
`InvalidClaimStateException(current, target)`. The API maps it to 409 `INVALID_CLAIM_STATE`.

## Pre-auth transitions (app_spec §6.1)
PENDING → {APPROVED, PARTIALLY_APPROVED, REJECTED, QUERY_RAISED}; QUERY_RAISED → PENDING.
Override edges are separate, behind `override_policy.can_override()`.

## Matrix test pattern
```python
ALL = list(CaseStatus)
@pytest.mark.ac("AC-08")
@pytest.mark.parametrize("src,dst", [(a, b) for a in ALL for b in ALL if b not in ALLOWED_TRANSITIONS[a]])
def test_disallowed_transition_raises(src, dst):
    with pytest.raises(InvalidClaimStateException):
        transition(src, dst)
```

## Rules
- Services never assign `status` directly. They call `transition()`, then append a `case_events`
  row and a notification.
- SETTLED is mutation-locked. Only `close` is allowed (NFR-08).
