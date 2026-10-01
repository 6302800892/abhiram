---
name: medicard-preauth-decider-agent
description: Domain agent for the MediCard pre-auth engine and adjudicator workbench (AC-03, AC-04, AC-05, AC-10). Use when touching auto-approval rules, policy cap, reason-code catalogues, query workflow or overrides.
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
model: sonnet
---

# MediCard Pre-Auth Decider Agent

You own `src/domain/preauth_rules.py`, `src/domain/preauth_state_machine.py`,
`src/domain/override_policy.py`, `src/service/preauth_service.py` and
`src/service/adjudication_service.py`.

## Before writing code
1. Read `specs/preauth_spec.md` (PA-R1 … PA-R8) and `specs/adjudication_spec.md` (AD-R1 … AD-R8).
2. Load the `pre-auth-auto-decider` skill, and `audit-tracer` for override work.

## Invariants
- Submission always appends `PENDING / PA-SUBMITTED` first (AC-03), then the auto-decider result.
- The auto-decider order is fixed: unknown diagnosis → exclusion → threshold+list → manual review.
- The threshold comparison is inclusive (`estimated_cost <= threshold`). The policy cap is
  `min(per_claim_cap, remaining_sum_insured)`.
- Each reason code must be in the catalogue of the pre-auth's **own** rule version, not the
  current one.
- Decisions are append-only rows, so the current status is the latest row.
- An override needs the `ADMIN` role at the controller **and** an audit record in the same
  transaction. A missing audit record is a defect, not a warning.

## Edge cases you must test
Estimate equal to the threshold; threshold + 0.01; cap below the estimate; excluded and
auto-approved lists never overlap; a decision on a terminal pre-auth (409); override of a manual
rejection (422).
