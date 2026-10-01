---
name: pre-auth-auto-decider
description: Rule-driven pre-auth auto-decision reference for MediCard (AC-03, AC-04, AC-05, PA-R3/PA-R4/PA-R6). Load before editing preauth_rules.py, preauth_service.py, or coverage rule versions.
---

# Pre-Auth Auto-Decider

## Algorithm (pure, `src/domain/preauth_rules.py`)

```
decide(estimate, diagnosis, rule, remaining_sum_insured) -> AutoDecision
  if diagnosis not in ICD_STUB:              -> QUERY_RAISED        [PA-QUERY-UNKNOWN-DIAGNOSIS]
  if diagnosis in rule.excluded_diagnoses:   -> REJECTED            [PA-REJECTED-EXCLUSION]
  cap = min(rule.per_claim_cap, remaining_sum_insured)
  if estimate <= rule.auto_approve_threshold and diagnosis in rule.auto_approved_diagnoses:
      if estimate <= cap:                    -> APPROVED  amount=estimate  [PA-AUTO-APPROVED]
      else:                                  -> PARTIALLY_APPROVED amount=cap [PA-AUTO-CAPPED]
  otherwise                                  -> PENDING             [PA-MANUAL-REVIEW]
```

## Submission sequence (service)
1. Eligibility must be ELIGIBLE (PA-R2).
2. Insert the pre-auth with the `rule_version` in force, plus a claim case in `PRE_AUTH`.
3. Append decision `PENDING / PA-SUBMITTED / SYSTEM`.
4. Append the auto decision `/ SYSTEM`. If it is still PENDING, append `PENDING / PA-MANUAL-REVIEW`.
5. Append timeline events and notifications for each status change (AC-09).

## Boundary vectors (threshold 50000.00, cap 500000.00)
| estimate | diagnosis | expected |
|---|---|---|
| 40000.00 | auto list | APPROVED 40000.00 |
| 50000.00 | auto list | APPROVED 50000.00 (inclusive) |
| 50000.01 | auto list | PENDING |
| 30000.00 | not on list | PENDING |
| 30000.00 | excluded | REJECTED |
| 30000.00 | `ZZZ.9` (unknown) | QUERY_RAISED |
| 30000.00 with remaining 20000.00 | auto list | PARTIALLY_APPROVED 20000.00 |

## Pitfalls
- Validate reason codes against the pre-auth's own version catalogue, not the latest version.
- Never compare `Decimal` with `float`.
