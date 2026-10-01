"""Programmatic harness sprint driver built on the Claude Agent SDK.

Runs one Claude Harness Engine sprint for a dependency group:
    generator (implements stories, TDD) -> evaluator (verifies sprint contract)
    -> ratchet (retry generator with the evaluator's failures, max N attempts)
and appends the outcome to .claude/state/iteration-log.md.

Usage:
    poetry run python scripts/sdk_sprint_runner.py --group C [--attempts 3] [--budget-usd 20]

Requires ANTHROPIC_API_KEY (or an active `claude` login). Install with `poetry install --with agents`.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from agent_defs import REPO_ROOT, load_agent_definitions  # noqa: E402

HARNESS_AGENTS = ["generator", "evaluator", "security-reviewer"]
DOMAIN_AGENTS = {
    "A": ["medicard-eligibility-agent"],
    "B": ["medicard-preauth-decider-agent"],
    "C": ["medicard-settlement-agent", "medicard-state-machine-validator-agent"],
    "D": ["medicard-preauth-decider-agent", "medicard-audit-tracer-agent"],
    "E": [],
}


def build_options(group: str, budget_usd: float) -> object:
    from claude_agent_sdk import ClaudeAgentOptions

    agents = load_agent_definitions(HARNESS_AGENTS + DOMAIN_AGENTS.get(group, []))
    return ClaudeAgentOptions(
        cwd=str(REPO_ROOT),
        setting_sources=["project"],  # loads CLAUDE.md, .claude/settings.json hooks, skills
        system_prompt={"type": "preset", "preset": "claude_code"},
        permission_mode="acceptEdits",
        allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash", "Task"],
        agents=agents,
        max_turns=200,
        max_budget_usd=budget_usd,
    )


def generator_prompt(group: str, feedback: str | None) -> str:
    base = (
        f"Act as the harness orchestrator for sprint group {group}. Delegate implementation to the "
        f"`generator` subagent: read sprint-contracts/group-{group}.json, the stories it lists in "
        "specs/stories/, and the feature specs. Follow TDD: commit AC-tagged failing tests first "
        "(`test: ... (red)`), then implementation (`feat: ... (green)`), then refactor. Use the domain "
        "subagents for their slices. Never evaluate your own work."
    )
    if feedback:
        base += f"\n\nThe evaluator FAILED the previous attempt. Fix exactly these failures:\n{feedback}"
    return base


def evaluator_prompt(group: str) -> str:
    return (
        f"Delegate to the `evaluator` subagent: verify sprint-contracts/group-{group}.json against the "
        "running app (start it with `poetry run medicard`, health URL from project-manifest.json). Run "
        "every api_check, the Playwright journeys, and `poetry run pytest -q`. Write "
        f"specs/reviews/sprint-{group}-evaluator-report.md with a line `VERDICT: PASS` or `VERDICT: FAIL`."
    )


async def run_agent(prompt: str, options: object) -> str:
    from claude_agent_sdk import query
    from claude_agent_sdk.types import AssistantMessage, ResultMessage, TextBlock

    final = ""
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text, flush=True)
        elif isinstance(message, ResultMessage):
            final = message.result or ""
            print(f"[result] turns={message.num_turns} cost=${message.total_cost_usd} error={message.is_error}")
    return final


def read_verdict(group: str) -> tuple[bool, str]:
    report = REPO_ROOT / "specs" / "reviews" / f"sprint-{group}-evaluator-report.md"
    if not report.exists():
        return False, "evaluator report missing"
    text = report.read_text(encoding="utf-8")
    return "VERDICT: PASS" in text, text


def log_iteration(group: str, attempt: int, passed: bool) -> None:
    log = REPO_ROOT / ".claude" / "state" / "iteration-log.md"
    stamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    status = "PASS" if passed else f"FAIL (attempt {attempt})"
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"\n## Group {group} — SDK sprint runner\n- **Date:** {stamp}\n- **Status:** {status}\n")


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", required=True, choices=sorted(DOMAIN_AGENTS))
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--budget-usd", type=float, default=20.0)
    args = parser.parse_args()

    options = build_options(args.group, args.budget_usd)
    feedback: str | None = None
    for attempt in range(1, args.attempts + 1):
        await run_agent(generator_prompt(args.group, feedback), options)
        await run_agent(evaluator_prompt(args.group), options)
        passed, report = read_verdict(args.group)
        log_iteration(args.group, attempt, passed)
        if passed:
            print(f"Group {args.group}: PASS on attempt {attempt}. Next: /sprint-pr {args.group}")
            return 0
        feedback = report[-4000:]  # ratchet: feed the failures back to the generator
    print(f"Group {args.group}: still failing after {args.attempts} attempts — escalate to human.")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
