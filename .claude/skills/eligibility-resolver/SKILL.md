---
name: eligibility-resolver
description: Eligibility decision reference for MediCard (AC-02, EL-R4/EL-R5). Load before editing eligibility_rules.py, eligibility_service.py, or any code that decides ELIGIBLE / NOT_ELIGIBLE.
---

# Eligibility Resolver

## Decision table (evaluate in this order)

| # | Check | Reason code | Short-circuit? |
|---|---|---|---|
| 1 | Policy exists for `policy_number` | `ELG-POLICY-NOT-FOUND` | yes |
| 2 | `member_id` belongs to that policy | `ELG-MEMBER-NOT-COVERED` | yes |
| 3 | `policy.status == "ACTIVE"` | `ELG-POLICY-INACTIVE` | no |
| 4 | `cover_start <= today <= cover_end` | `ELG-OUTSIDE-COVER-PERIOD` | no |
| 5 | `remaining_sum_insured > 0` | `ELG-SUM-INSURED-EXHAUSTED` | no |
| 6 | Requesting hospital `in_network` | `ELG-HOSPITAL-NOT-NETWORK` | no |

No reasons ⇒ `ELIGIBLE` and `["ELG-OK"]`. Otherwise `NOT_ELIGIBLE` and the reasons in table order.

## Shape

```python
@dataclass(frozen=True)
class EligibilityInput:
    policy: PolicySnapshot | None
    member_on_policy: bool
    remaining_sum_insured: Decimal
    hospital_in_network: bool
    today: date

def resolve_eligibility(inp: EligibilityInput) -> EligibilityResult: ...
```

The function is pure. The service does all I/O and builds `EligibilityInput`.

## Test vectors
- Active, in period, remaining 1.00, in network ⇒ ELIGIBLE.
- Remaining exactly 0.00 ⇒ `ELG-SUM-INSURED-EXHAUSTED`.
- `today == cover_end` ⇒ still in period (inclusive both ends).
- Lapsed and expired ⇒ two codes, in order 3 then 4.

## Pitfalls
- Do not read the hospital from the request body. Use the principal's `hospital_id`.
- Do not return member DOB or diagnosis in the response or logs.
