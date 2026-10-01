# src/domain/ — pure cashless-health rules

No I/O, no frameworks, no logging, no `datetime.now()` (use the injected `Clock`).
Everything here is deterministic and unit-tested in `tests/unit/`.

| File | Owns | Spec |
|---|---|---|
| `money.py` | Decimal parsing / HALF_UP quantization / float rejection | NFR-01 |
| `eligibility_rules.py` | ELIGIBLE / NOT_ELIGIBLE decision table | AC-02, EL-R4 |
| `coverage_rules.py` | Versioned coverage rule + validation, reason catalogue | NA-R3, NA-R5 |
| `preauth_rules.py` | Auto-decider (threshold, auto list, exclusion, cap) | AC-05, PA-R4 |
| `preauth_state_machine.py` | Pre-auth transitions | AC-04 |
| `claim_state_machine.py` | Case transitions, `InvalidClaimStateException` | AC-08 |
| `bill_rules.py` | `pre_auth_amount + buffer` cap | AC-06, ST-R1 |
| `settlement_calculator.py` | Settlement formula + invariant | AC-07, ST-R2/R3 |
| `override_policy.py` | Who/what may be overridden | AC-10, AD-R6 |
| `report_metrics.py` | Turnaround, query rate, loss ratio math | Reports |
| `icd_stub.py` | Static ICD-10 / procedure stub | brief 6.3 |

Skills: `eligibility-resolver`, `pre-auth-auto-decider`, `settlement-calculator`, `claim-state-machine`.
At least 4 rule/policy/validator files live here (business-understanding rubric).
