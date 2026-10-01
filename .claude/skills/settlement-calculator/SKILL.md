---
name: settlement-calculator
description: Fixed-point settlement and bill-cap math for MediCard (AC-06, AC-07, NFR-01, ST-R1–ST-R4). Load before touching money.py, bill_rules.py, settlement_calculator.py, settlement_service.py or any Decimal arithmetic.
---

# Settlement Calculator

## Formulas
```
cap        = q(pre_auth_amount + pre_auth_amount * buffer_pct / 100)
admissible = min(final_bill, cap)
ded        = min(deductible, admissible)
copay      = q((admissible - ded) * copay_pct / 100)
settlement = admissible - ded - copay           # invariant: 0 <= settlement <= admissible
q(x)       = x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

## Mandatory code shape
```python
def calculate_settlement(inp: SettlementInput) -> SettlementBreakdown:
    require_decimal(...)              # raises TypeError on float
    ...
    assert_settlement_invariant(settlement, admissible)   # raises SettlementInvariantError
    return SettlementBreakdown(...)
```
The `settlement-cap-check.sh` hook rejects any file defining or calling settlement computation
without `assert_settlement_invariant`.

## Worked vectors
| pre_auth | buffer % | bill | ded | copay % | admissible | copay | settlement |
|---|---|---|---|---|---|---|---|
| 100000.00 | 10 | 90000.00 | 5000.00 | 10 | 90000.00 | 8500.00 | 76500.00 |
| 100000.00 | 10 | 120000.00 | 0.00 | 0 | 110000.00 | 0.00 | 110000.00 |
| 100000.00 | 10 | 3000.00 | 5000.00 | 20 | 3000.00 | 0.00 | 0.00 |
| 1000.00 | 10 | 1000.05 | 0.00 | 10 | 1000.05 | 100.01 | 900.04 |
| 100000.00 | 0 | 100000.00 | 0.00 | 0 | 100000.00 | 0.00 | 100000.00 |

## Pitfalls
- `Decimal(0.1)` is wrong. Use `Decimal("0.1")` and parse money from strings.
- Quantize only at the defined points. Quantizing earlier changes the half-up results.
- Persist all breakdown fields as strings. SQLite REAL would reintroduce float.
