"""Deterministic AC traceability check (programmatic form of /ac-trace).

Every AC-NN listed in specs/app_spec.md must be referenced by at least one test under tests/ or
frontend/e2e/. Writes specs/reviews/ac-trace.md and exits 1 on any gap.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
AC_ROW = re.compile(r"^\| (AC-\d{2}) \|", re.MULTILINE)
TEST_GLOBS = [("tests", "test_*.py"), ("frontend/e2e", "*.spec.ts")]


def spec_acs() -> list[str]:
    return sorted(set(AC_ROW.findall((ROOT / "specs" / "app_spec.md").read_text(encoding="utf-8"))))


def test_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for folder, pattern in TEST_GLOBS:
        base = ROOT / folder
        if base.exists():
            files.extend(sorted(base.rglob(pattern)))
    return files


def references(ac: str, text: str) -> int:
    compact = ac.replace("-", "").lower()  # AC-07 -> ac07 (test function names)
    return len(re.findall(rf"{re.escape(ac)}(?:\.\d+)?\b", text)) + len(re.findall(rf"\b\w*{compact}\w*", text))


def main() -> int:
    rows, gaps = [], []
    sources = {path: path.read_text(encoding="utf-8") for path in test_files()}
    for ac in spec_acs():
        hits = {p: references(ac, t) for p, t in sources.items() if references(ac, t)}
        status = "COVERED" if hits else "GAP"
        if not hits:
            gaps.append(ac)
        names = ", ".join(f"`{p.relative_to(ROOT).as_posix()}`" for p in hits) or "—"
        rows.append(f"| {ac} | {names} | {sum(hits.values())} | {status} |")
    verdict = "VERDICT: FAIL" if gaps else "VERDICT: PASS"
    report = ["# AC Traceability", "", "| AC | Test files | References | Status |", "|---|---|---|---|", *rows, "",
              verdict, ""]
    out = ROOT / "specs" / "reviews" / "ac-trace.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))
    return 1 if gaps else 0


if __name__ == "__main__":
    sys.exit(main())
