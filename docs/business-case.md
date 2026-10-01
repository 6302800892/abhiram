# MediCard — Business Case (BC-AINE-017)

> Domain: Insurance — Health Cashless. This is the business context the reviewer plugin reads.
> Detailed requirements live in `specs/app_spec.md`. The BRD is `specs/brd/brd.md`.

## 1. Problem

In cashless hospitalization, the insurer pays the network hospital directly, so the patient does
not pay up front and claim back later. The value of cashless depends entirely on speed and trust
between three parties who do not share a system:

- **The hospital** needs to know at the admission desk whether the patient is covered. It then
  needs a pre-authorization decision before treatment and, after discharge, payment of the bill.
- **The insurer** must decide pre-auths quickly without over-committing money. It must also stop
  bills that exceed what was authorized, and pay the correct amount after deductibles and co-pay.
- **The customer** is anxious and blind. They do not know whether the case is approved, queried or
  stuck, or why the payout differed from the bill.

Today this runs on phone calls, PDFs and spreadsheets. Decisions take hours. Bill overruns are
found at discharge. Settlement arithmetic is error-prone. Override decisions cannot be audited.

## 2. Target Users

| User | What they do in MediCard |
|---|---|
| Customer (policy holder / member) | Registers, links a policy, views sum insured, exclusions and network hospitals, tracks the case timeline, and sees the post-discharge settlement breakdown |
| Network hospital | Looks up eligibility by member ID and policy, submits pre-auth, answers queries, records admission, procedures, discharge and the final bill, and tracks its **own** cases only |
| Insurer adjudicator | Works the manual review queue (queried or large pre-auths), decides with reason codes, disputes or settles discharged cases |
| Insurer admin | Maintains network hospitals, policy products and **versioned** coverage rules, overrides auto-rejected or escalated pre-auths (audited), and reads reports |

## 3. Value Proposition

- **Instant decisions for routine cases.** A rule engine auto-approves pre-auths when the estimate
  is within the configured threshold and the diagnosis is on the auto-approved list, capped at the
  policy limit. Hospitals get an answer at submission time.
- **No surprise overruns.** A final bill above `pre_auth_amount + buffer %` is refused when it is
  submitted, not discovered at settlement.
- **Correct, explainable payouts.** Settlement uses
  `min(final_bill, pre_auth_amount + buffer) − deductible − co-pay`, computed in fixed-point decimal.
  The result is never negative, and the full breakdown is shown to the customer.
- **Trust through audit.** Decisions, bills, settlements and overrides are append-only. Every admin
  override records who did it, when, and why.
- **Transparency for the patient.** Every state change produces a notification and a timeline
  entry that both the hospital and the customer can see.

## 4. Domain Rules

| Rule | Statement | Source |
|---|---|---|
| Eligibility | A member is ELIGIBLE only if the policy exists, the member is on it, the policy is ACTIVE, today is inside the cover period, sum insured is not exhausted, and the requesting hospital is in network. Otherwise NOT_ELIGIBLE with reason codes | AC-02 |
| Pre-auth entry | A submitted pre-auth always starts in PENDING | AC-03 |
| Pre-auth outcomes | PENDING → APPROVED / PARTIALLY_APPROVED / REJECTED / QUERY_RAISED, each with reason codes from the coverage-rule version in force | AC-04 |
| Auto-approval | `estimated_cost ≤ threshold` AND diagnosis in the auto-approved list ⇒ approved up to `min(per-claim cap, remaining sum insured)` | AC-05 |
| Bill cap | `final_bill ≤ pre_auth_amount × (1 + buffer %)` | AC-06 |
| Settlement | `min(final_bill, pre_auth_amount + buffer) − deductible − co-pay`, and `settlement ≥ 0` | AC-07 |
| Case lifecycle | PRE_AUTH → ADMITTED → DISCHARGED → SETTLED / DISPUTED → CLOSED. Anything else raises `InvalidClaimStateException` | AC-08 |
| Notification | The customer is notified of every state transition, and the timeline is visible to customer and hospital | AC-09 |
| Override | Only the insurer admin may override an auto-rejected or escalated (queried) pre-auth. A reason is mandatory, and actor and timestamp are audited | AC-10 |
| Money | Fixed-point decimal only, never float | NFR-01 |
| Immutability | Decisions, bills, settlements and overrides are append-only, and settled cases cannot be mutated | NFR-02, NFR-08 |
| Privacy | Diagnosis, procedure and health history are never logged in plaintext | NFR-03 |
| Segregation | Role checks at the controller. Hospitals see only their own cases | NFR-04 |

## 5. Success Metrics

| Metric | Target | How it is measured |
|---|---|---|
| Rule-eligible pre-auths auto-decided | 100 % at submission | AC-05 tests and the turnaround report |
| Manual pre-auth turnaround | Tracked per period | `GET /api/reports/summary` → `preauth_turnaround_hours` |
| Bills above cap accepted | 0 | AC-06 tests and architecture test |
| Negative or over-cap settlements | 0 | AC-07 property-style edge-case tests |
| Overrides without audit record | 0 | AC-10 tests and architecture test |
| PHI leaks in logs | 0 | NFR-03 log-capture test and `phi-redaction-check` hook |
| Query rate by hospital | Visible to admin | Reports |
| Average loss ratio | Visible to admin | Reports (settled ÷ premium) |

## 6. Out of Scope

Real HIS / EMR integration, real payments (the payment trigger is stubbed), a real ICD-10 master (a
static stub of about 12 codes is used), fraud modelling, multi-currency, and production
deployment. Only synthetic data is used. No real or Virtusa-confidential data appears anywhere.
