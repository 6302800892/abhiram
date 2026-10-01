"""NFR-04 foundations: password hashing and signed tokens (no plaintext, tamper-evident)."""

import datetime as dt

import pytest

from src.domain.exceptions import AuthenticationError
from src.service.auth_service import hash_password, issue_token, verify_password, verify_token

NOW = dt.datetime(2026, 6, 15, 10, 0, tzinfo=dt.UTC)


def test_password_hash_is_not_plaintext_and_verifies() -> None:
    stored = hash_password("Demo@1234", iterations=1_000)
    assert "Demo@1234" not in stored
    assert verify_password("Demo@1234", stored)
    assert not verify_password("wrong", stored)


def test_token_round_trip() -> None:
    token = issue_token(user_id=7, role="HOSPITAL", secret="s", now=NOW, ttl_hours=1)
    claims = verify_token(token, secret="s", now=NOW)
    assert claims.user_id == 7 and claims.role == "HOSPITAL"


def test_tampered_token_rejected() -> None:
    token = issue_token(user_id=7, role="HOSPITAL", secret="s", now=NOW, ttl_hours=1)
    payload, sig = token.split(".")
    with pytest.raises(AuthenticationError):
        verify_token(payload + "x." + sig, secret="s", now=NOW)
    with pytest.raises(AuthenticationError):
        verify_token(token, secret="other", now=NOW)


def test_expired_token_rejected() -> None:
    token = issue_token(user_id=7, role="ADMIN", secret="s", now=NOW, ttl_hours=1)
    with pytest.raises(AuthenticationError):
        verify_token(token, secret="s", now=NOW + dt.timedelta(hours=2))
