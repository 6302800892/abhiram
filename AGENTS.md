# AGENTS.md — Table of Contents

This file is an index only. Rules live in the files it points to.

## Context
- [CLAUDE.md](CLAUDE.md) — root rules and quick reference
- [docs/business-case.md](docs/business-case.md) — business context
- [specs/app_spec.md](specs/app_spec.md) — acceptance criteria and NFRs (source of truth)
- [docs/architecture.md](docs/architecture.md) — layers and diagrams
- [docs/tdd.md](docs/tdd.md) — red-green-refactor discipline

## Module guides (CLAUDE.md hierarchy)
- [src/CLAUDE.md](src/CLAUDE.md) · [src/domain/CLAUDE.md](src/domain/CLAUDE.md) · [src/config/CLAUDE.md](src/config/CLAUDE.md)
- [src/repository/CLAUDE.md](src/repository/CLAUDE.md) · [src/service/CLAUDE.md](src/service/CLAUDE.md) · [src/api/CLAUDE.md](src/api/CLAUDE.md)
- [tests/CLAUDE.md](tests/CLAUDE.md) · [tests/architecture/CLAUDE.md](tests/architecture/CLAUDE.md)
- [migrations/CLAUDE.md](migrations/CLAUDE.md) · [frontend/CLAUDE.md](frontend/CLAUDE.md) · [specs/CLAUDE.md](specs/CLAUDE.md)

## Harness agents (`.claude/agents/`)
- planner · generator · evaluator · test-engineer · security-reviewer · design-critic · ui-designer

## Project agents (`.claude/agents/`)
- medicard-eligibility-agent · medicard-preauth-decider-agent · medicard-settlement-agent
- medicard-state-machine-validator-agent · medicard-archtest-author-agent · medicard-audit-tracer-agent
- medicard-janitor-agent (bonus) · medicard-doc-writer-agent (bonus)

## Project skills (`.claude/skills/`)
- eligibility-resolver · pre-auth-auto-decider · settlement-calculator · claim-state-machine · phi-safe-logging · audit-tracer

## Project commands (`.claude/commands/`)
- /ac-trace · /settlement-audit · /sprint-pr

## Project hooks (`.claude/hooks/`)
- phi-redaction-check.sh · settlement-cap-check.sh · role-boundary-check.sh · money-float-check.sh · append-only-migration-check.sh

## Packaging
- [plugin.json](plugin.json) — MediCard substrate plugin · [.mcp.json](.mcp.json) — Playwright MCP
- [scripts/](scripts/) — Claude Agent SDK automation
