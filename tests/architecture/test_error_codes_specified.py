"""Spec-Is-Truth rule (learned rule 2): every error code the code can return is documented in specs/."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAISED = re.compile(r'(?:Error|Exception)\(\s*"([A-Z][A-Z_]{3,})"|code="([A-Z][A-Z_]{3,})"')
ENVELOPE = re.compile(r'"([A-Z][A-Z_]{3,})"')  # literal codes in the API error mapper


def _raised_codes() -> set[str]:
    codes: set[str] = set()
    for path in (ROOT / "src").rglob("*.py"):
        for match in RAISED.finditer(path.read_text(encoding="utf-8")):
            codes.add(match.group(1) or match.group(2))
    codes |= set(ENVELOPE.findall((ROOT / "src" / "api" / "errors.py").read_text(encoding="utf-8")))
    exceptions = (ROOT / "src" / "domain" / "exceptions.py").read_text(encoding="utf-8")
    codes |= set(re.findall(r'super\(\).__init__\("([A-Z][A-Z_]{3,})"', exceptions))
    return codes


def test_discovery_finds_known_codes() -> None:
    """Tripwire against a vacuous pass (learned rule 3)."""
    assert {"BILL_EXCEEDS_CAP", "INVALID_CLAIM_STATE", "OVERRIDE_NOT_ALLOWED", "VALIDATION_ERROR"} <= _raised_codes()


def test_every_raised_error_code_is_in_a_spec() -> None:
    spec_text = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "specs").glob("*.md"))
    missing = sorted(c for c in _raised_codes() if not re.search(rf"\b{c}\b", spec_text))
    assert missing == [], f"undocumented error codes (add them to specs/app_spec.md §7.1): {missing}"
