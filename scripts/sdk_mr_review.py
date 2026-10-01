"""Claude Agent SDK merge-request reviewer used by the GitLab `claude-review` CI job.

Runs the harness `security-reviewer` plus the MediCard `medicard-audit-tracer-agent` and
`medicard-state-machine-validator-agent` (read-only) against the MR diff. Writes
specs/reviews/mr-review.md and exits 1 if the review contains `VERDICT: FAIL`.

Usage (CI): python scripts/sdk_mr_review.py --base "$CI_MERGE_REQUEST_DIFF_BASE_SHA"
"""

from __future__ import annotations

import argparse
import asyncio
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from agent_defs import REPO_ROOT, load_agent_definitions  # noqa: E402

REVIEWERS = ["security-reviewer", "medicard-audit-tracer-agent", "medicard-state-machine-validator-agent"]
REPORT = REPO_ROOT / "specs" / "reviews" / "mr-review.md"

PROMPT = """You are reviewing a MediCard merge request. Changed files:
{files}

Delegate in parallel to the subagents {reviewers}. Check against specs/app_spec.md:
- NFR-01 Decimal money, NFR-02 append-only, NFR-03 no PHI in logs, NFR-04 role checks / hospital
  isolation, NFR-08 settled immutability, bill cap, override audit.
- Every changed AC has an AC-tagged test.
Do not modify any file except {report}. Write findings there as a table
(severity | file:line | rule | finding) and end with `VERDICT: PASS` (no CRITICAL/HIGH) or `VERDICT: FAIL`."""


def changed_files(base: str) -> list[str]:
    out = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"], capture_output=True, text=True,
                         cwd=REPO_ROOT, check=True)
    return [line for line in out.stdout.splitlines() if line.strip()]


async def review(files: list[str]) -> None:
    from claude_agent_sdk import ClaudeAgentOptions, query
    from claude_agent_sdk.types import ResultMessage

    options = ClaudeAgentOptions(
        cwd=str(REPO_ROOT),
        setting_sources=["project"],
        permission_mode="acceptEdits",
        allowed_tools=["Read", "Glob", "Grep", "Bash(git diff:*)", "Bash(git log:*)", "Write", "Task"],
        agents=load_agent_definitions(REVIEWERS),
        max_turns=60,
    )
    prompt = PROMPT.format(files="\n".join(f"- {f}" for f in files), reviewers=", ".join(REVIEWERS),
                           report=REPORT.relative_to(REPO_ROOT).as_posix())
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            print(f"[claude-review] turns={message.num_turns} cost=${message.total_cost_usd}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    args = parser.parse_args()
    files = changed_files(args.base)
    if not files:
        print("No changes to review.")
        return 0
    asyncio.run(review(files))
    text = REPORT.read_text(encoding="utf-8") if REPORT.exists() else "VERDICT: FAIL (no report written)"
    print(text)
    return 1 if "VERDICT: FAIL" in text else 0


if __name__ == "__main__":
    raise SystemExit(main())
