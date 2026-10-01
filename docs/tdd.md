# TDD Discipline — red → green → refactor

Every story was built test-first by the generator, which follows the harness
`test-driven-development` skill and `.claude/skills/code-gen/SKILL.md`. The evaluator then
verified each sprint independently against the running app.

## The loop we follow

1. **Spec → test (red).** Turn each Given-When-Then criterion in `specs/*_spec.md` into a test
   tagged `@pytest.mark.ac("AC-NN")` (or `nfr`), with `acNN` in the name. Run it and **save the
   failing output** to `specs/test_artefacts/sprint-<G>-red.txt`.
2. **Minimal code (green).** Implement the pure rule in `src/domain/` first, then the service, then
   the route. Run the whole suite.
3. **Refactor.** Remove duplication and hacks while the suite stays green. The guardrail hooks
   (`.claude/hooks/*.sh`) run on every edit.
4. **Evaluate.** A separate evaluator agent runs the sprint contract against the live app. Its
   failures go back through steps 1–3 (see `docs/fix-loops/`).

## Evidence per sprint

| Sprint | Red run | Green | Refactor example |
|---|---|---|---|
| A — eligibility, admin | `specs/test_artefacts/sprint-A-red.txt` (`No module named 'src'`) | 139 → 225 tests | Removed the `# require_roles(` comment hack; the hook learns guard aliases (KD-02) |
| B — pre-auth, adjudication | `sprint-B-red.txt` (`No module named 'src.domain.preauth_state_machine'`) | 223 | `MediCardError.details` added so NOT_ELIGIBLE carries reason codes |
| C — admission, settlement | `sprint-C-red.txt` (4 collection errors) | 361 | `policy_repo.settled_total` `sqlite_master` probe replaced by `settlement_repo`; the `if False` hack in `settle` removed |
| D — override, reports | `sprint-D-red.txt` (3 collection errors) | 414 | `sum()` given a Decimal start (mypy caught a float leak) |
| E — portal UI | `sprint-E-red.txt` (journeys fail, no UI) | 22 Playwright journeys | Brittle data-bearing snapshots narrowed to static panels |
| Fix loop FL-001 | `docs/fix-loops/FL-001-reproduce.txt` | 421 | Rule-version lookup centralised in `case_service.case_rule` |

Test files: `tests/unit/` (14 files), `tests/api/` (11), `tests/architecture/` (7) and
`frontend/e2e/` (6 specs). Together that is far beyond the 10-file minimum.

## Worked example — AC-07 settlement-cap edge cases

**Spec** (`specs/settlement_spec.md`, ST-R2/ST-R3):
`settlement = min(final_bill, cap) − min(D, admissible) − copay`, with
`copay = (admissible − deductible_applied) × c / 100` (HALF_UP) and `0 ≤ settlement ≤ admissible`.

### Red

```python
# tests/unit/test_settlement_calculator.py — written before settlement_calculator.py existed
@pytest.mark.ac("AC-07")
def test_ac07_1_worked_example() -> None:
    b = _calc("100000.00", "10", "90000.00", "5000.00", "10")
    assert (b.cap, b.admissible, b.deductible_applied, b.copay, b.settlement_amount) == (
        D("110000.00"), D("90000.00"), D("5000.00"), D("8500.00"), D("76500.00"))

@pytest.mark.ac("AC-07")
def test_ac07_3_deductible_larger_than_bill_never_negative() -> None:
    b = _calc("100000.00", "10", "3000.00", "5000.00", "20")
    assert b.settlement_amount == D("0.00")

@pytest.mark.ac("AC-07")
def test_ac07_4_copay_rounds_half_up() -> None:          # 100.005 -> 100.01
    b = _calc("1000.00", "10", "1000.05", "0.00", "10")
    assert (b.copay, b.settlement_amount) == (D("100.01"), D("900.04"))
```

Red output (`specs/test_artefacts/sprint-C-red.txt`):
`ERROR tests/unit/test_settlement_calculator.py` because `src.domain.settlement_calculator` did not exist.

### Green

A minimal `calculate_settlement` quantizes only where the spec says (cap and co-pay), then
calls `assert_settlement_invariant` before returning. The edge-case grid
`test_ac07_invariant_holds_across_grid` covers 7 bills × 4 co-pay rates, including 0.01,
4999.99, the cap boundary and 999999.99. It asserts `0 ≤ settlement ≤ admissible ≤ cap` and
`settlement + deductible + copay == admissible`.

### Refactor

The cap formula moved into `bill_rules.bill_cap` so the AC-06 bill check and the AC-07 settlement
share one implementation. The `settlement-cap-check.sh` hook now blocks any settlement code that
lacks the invariant call. `tests/architecture/test_bill_cap_enforced.py` makes the same rule
structural.

### When green was not enough

All AC-07 tests were green, yet the Sprint 3 evaluator found that publishing a new rule version
mid-cycle changed an existing case's cap. No test had varied the rule version between approval and
settlement. Fix loop **FL-001** added that red test first (`test_c01b_…`) and amended ST-R1, then
fixed the code. It also added an architecture test that bans `current_rule()` on money paths.
