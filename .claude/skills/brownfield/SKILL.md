---
name: brownfield
description: Discover and map an existing codebase before planning or changing it.
argument-hint: "[optional-focus-path-or-goal]"
context: fork
agent: planner
---

# Brownfield Discovery

Use `/brownfield` in existing repositories before substantial planning, improvements, refactors, or bug work. The goal is to build a factual map of the current system so agents respect the codebase instead of inventing a parallel architecture.

This skill does not change production code.

---

## Usage

```text
/brownfield
/brownfield backend/src
/brownfield "map auth and billing before adding team invites"
```

---

## Outputs

Write these files:

| File | Purpose |
|---|---|
| `specs/brownfield/codebase-map.md` | Languages, frameworks, package managers, entry points, services, commands |
| `specs/brownfield/code-graph.json` | Deterministic dependency graph (produced by `/code-map`) |
| `specs/brownfield/dependency-graph.md` | Mermaid render of the file/module-level edges |
| `specs/brownfield/coupling-report.md` | Fan-in / fan-out / cycles / unstable hubs |
| `specs/brownfield/architecture-map.md` | Modules, layers, data flow, public interfaces, external dependencies — cites the graph |
| `specs/brownfield/test-map.md` | Test commands, coverage signals, public interfaces covered/missing, slow/flaky tests |
| `specs/brownfield/risk-map.md` | Sensitive areas, fragile zones, structural risks (cycles, hubs without tests), auth/security/billing/data risks |
| `specs/brownfield/change-strategy.md` | Recommended lane for future work: `/vibe`, `/fix-issue`, `/improve`, `/refactor`, `/spec`, `/auto` |
| `CONTEXT.md` | Optional domain glossary, created only when meaningful domain terms are discovered |

---

## Step 1 — Inventory the Repo

Discover facts, not guesses:

- Languages and frameworks
- Package managers and lockfiles
- App entry points
- Test/build/lint/typecheck commands
- Runtime services and Docker/compose files
- Environment/config files
- CI workflows
- Database migrations or schema files
- Public API route definitions
- Frontend routes/screens

Use `rg`, `find`, package manifests, config files, and existing docs. Prefer primary repo evidence over assumptions.

---

## Step 1.5 — Build the Dependency Graph

Run `/code-map` (or invoke its script directly) to produce a deterministic graph the rest of this skill cites as evidence:

```bash
node .claude/skills/code-map/scripts/build_graph.js \
  --root . --out specs/brownfield/code-graph.json
node .claude/skills/code-map/scripts/build_graph.js \
  --render-mermaid specs/brownfield/code-graph.json \
  --out specs/brownfield/dependency-graph.md
node .claude/skills/code-map/scripts/build_graph.js \
  --coupling-report specs/brownfield/code-graph.json \
  --out specs/brownfield/coupling-report.md
```

If the `graphify` skill or `hex-graph` MCP server is available, prefer them and project the result into the same `code-graph.json` schema (see `.claude/skills/code-map/SKILL.md` § Resolution Order).

If the graph comes back empty or with all warnings, stop and report. Do not invent architecture from filenames.

## Step 2 — Map Architecture

Write `architecture-map.md` with:

- Major modules and their responsibilities — cite specific edges from `code-graph.json`
- Public interfaces for each major module — symbols list per file is in the graph
- Data flow through the system — follow `imports` / `calls` chains
- External integrations — `ext:*` targets in the graph
- Persistence boundaries
- Auth/session boundaries
- Existing layering conventions — confirm with directional fan-in/fan-out from the coupling report
- Deep modules worth preserving — high fan-in, low instability
- Shallow/pass-through modules that may be refactor candidates — high instability, no domain logic

Every "module X depends on Y" claim must reference an edge from `code-graph.json` (file:line evidence). Do not redesign the system. Capture what exists.

---

## Step 3 — Map Tests

Write `test-map.md` with:

- Test frameworks and commands
- Unit/integration/e2e locations
- Which public interfaces are covered
- Which critical public interfaces lack tests
- Known slow/flaky tests if discoverable
- Whether tests isolate env/config correctly

If commands are obvious and safe, run lightweight discovery commands such as `npm test -- --help`, `pytest --collect-only`, or package script listing. Do not run expensive test suites unless the user asked.

---

## Step 4 — Map Risks

Write `risk-map.md` with:

### Domain risks
- Auth, permissions, privacy, billing, payment, and security-sensitive paths
- Database migrations and irreversible data operations
- External APIs and side-effecting integrations
- Generated code or vendored code that should not be edited manually

### Structural risks (read from `coupling-report.md`)
- **Cycles** — files inside the SCC; refactors that cross a cycle boundary need explicit approval
- **Hub modules without tests** — high fan-in files that lack a corresponding test target in `test-map.md`
- **Unstable hubs** — fan_in ≥ 5 with instability ≥ 0.8 (heavy dependents, lots of outgoing churn)
- **Orphan files** — fan_in == 0 and not an entrypoint (potential dead code)

For each risk, include the evidence path or graph node id.

---

## Step 5 — Recommend Change Strategy

Write `change-strategy.md` with:

- What qualifies for `/vibe`
- What should use `/fix-issue`
- What should use `/improve`
- What should use `/refactor`
- What requires `/spec` → `/design` → `/auto`
- What should require explicit human approval before touching

Include a short "first safe next steps" list.

---

## Step 6 — Domain Glossary

If recurring domain terms are discovered, create or update `CONTEXT.md`.

Keep it domain-level:

```markdown
# Context

## Terms

### Account
Definition meaningful to users/domain experts.

### User
Definition and how it differs from Account.
```

Do not fill `CONTEXT.md` with implementation details.

---

## Gate

Before recommending implementation, present:

- What the system appears to be
- Highest-risk areas
- Existing test confidence
- Recommended lane for the requested work
- Any uncertainty that needs human confirmation

Do not proceed to code changes from `/brownfield` unless the user explicitly asks.

---

## Gotchas

- **Do not invent architecture.** If evidence is missing, say unknown.
- **Do not create parallel implementations.** Brownfield work modifies existing paths unless a story/design explicitly approves a replacement.
- **Do not trust names alone.** Confirm responsibilities from imports, tests, route wiring, and callers.
- **Do not over-map the universe.** Focus enough to guide safe future changes.
- **Do not run destructive commands.** Discovery is read-only except for writing brownfield docs and optional `CONTEXT.md`.
