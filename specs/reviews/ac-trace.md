# AC Traceability

| AC | Test files | References | Status |
|---|---|---|---|
| AC-01 | `tests/api/test_ac01_customer_coverage.py`, `frontend/e2e/customer.spec.ts` | 18 | COVERED |
| AC-02 | `tests/api/test_ac02_eligibility.py`, `tests/api/test_network_admin.py`, `tests/unit/test_eligibility_rules.py`, `frontend/e2e/hospital.spec.ts` | 34 | COVERED |
| AC-03 | `tests/api/test_ac03_ac05_preauth.py`, `frontend/e2e/hospital.spec.ts` | 12 | COVERED |
| AC-04 | `tests/api/test_ac03_ac05_preauth.py`, `tests/api/test_ac04_adjudication.py`, `tests/unit/test_preauth_rules.py`, `tests/unit/test_preauth_state_machine.py`, `frontend/e2e/insurer-admin.spec.ts` | 49 | COVERED |
| AC-05 | `tests/api/test_ac03_ac05_preauth.py`, `tests/unit/test_preauth_rules.py`, `frontend/e2e/hospital.spec.ts` | 19 | COVERED |
| AC-06 | `tests/api/test_ac06_ac08_case_lifecycle.py`, `tests/api/test_fix_loop_rule_version.py`, `tests/unit/test_bill_rules.py`, `frontend/e2e/hospital.spec.ts` | 22 | COVERED |
| AC-07 | `tests/api/test_ac07_settlement.py`, `tests/api/test_fix_loop_rule_version.py`, `tests/unit/test_settlement_calculator.py`, `frontend/e2e/customer.spec.ts` | 37 | COVERED |
| AC-08 | `tests/api/test_ac06_ac08_case_lifecycle.py`, `tests/api/test_fix_loop_rule_version.py`, `tests/unit/test_claim_state_machine.py`, `frontend/e2e/hospital.spec.ts` | 24 | COVERED |
| AC-09 | `tests/api/test_ac09_timeline_notifications.py`, `frontend/e2e/customer.spec.ts` | 11 | COVERED |
| AC-10 | `tests/api/test_ac10_override_audit.py`, `tests/api/test_security_hardening.py`, `tests/architecture/test_override_audited.py`, `tests/unit/test_override_policy.py`, `tests/unit/test_preauth_state_machine.py`, `frontend/e2e/insurer-admin.spec.ts` | 38 | COVERED |

VERDICT: PASS
