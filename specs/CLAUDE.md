# specs/ — source of truth (Spec-Is-Truth Rule)

- `app_spec.md` is the root: ACs, NFRs and state machines. The feature specs (`*_spec.md`) own
  the business rules (`EL-R*`, `PA-R*`, `AD-R*`, `AM-R*`, `ST-R*`, `NA-R*`, `RP-R*`) and
  Given-When-Then criteria.
- When code and spec disagree, change the spec deliberately first. Record the reason in a
  "Change log" section, then regenerate the code and tests.
- `brd/` is the harness `/brd` output. `stories/` and `../features.json` are the harness `/spec`
  output.
- `reviews/` holds evaluator, security, AC-trace and settlement-audit reports, each with a
  `VERDICT:` line. `test_artefacts/` holds red-phase runs (TDD evidence).
