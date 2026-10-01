"""Password hashing (PBKDF2-SHA256) and HMAC-signed bearer tokens. Standard library only."""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import json
import secrets
import sqlite3
from dataclasses import dataclass

from src.domain.enums import Role
from src.domain.exceptions import AuthenticationError
from src.domain.principal import Principal
from src.repository import user_repo

_ALGO = "pbkdf2_sha256"
_DUMMY_HASH = f"{_ALGO}$200000${'00' * 16}${'00' * 32}"  # never matches; used only for timing parity


@dataclass(frozen=True)
class TokenClaims:
    user_id: int
    role: str
    expires_at: int


def hash_password(password: str, *, iterations: int) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"{_ALGO}${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    if algo != _ALGO:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
    return hmac.compare_digest(digest.hex(), digest_hex)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(payload: str, secret: str) -> str:
    return _b64(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())


def issue_token(*, user_id: int, role: str, secret: str, now: dt.datetime, ttl_hours: int) -> str:
    exp = int((now + dt.timedelta(hours=ttl_hours)).timestamp())
    payload = _b64(json.dumps({"sub": user_id, "role": role, "exp": exp}, separators=(",", ":")).encode())
    return f"{payload}.{_sign(payload, secret)}"


def verify_token(token: str, *, secret: str, now: dt.datetime) -> TokenClaims:
    payload, _, signature = token.partition(".")
    expected = _sign(payload, secret).encode()
    if not payload or not signature or not hmac.compare_digest(expected, signature.encode("utf-8", "surrogateescape")):
        raise AuthenticationError("invalid token")
    try:
        data = json.loads(_unb64(payload))
        claims = TokenClaims(int(data["sub"]), str(data["role"]), int(data["exp"]))
    except (ValueError, KeyError, TypeError) as exc:
        raise AuthenticationError("invalid token") from exc
    if claims.expires_at <= int(now.timestamp()):
        raise AuthenticationError("token expired")
    return claims


def authenticate(conn: sqlite3.Connection, username: str, password: str) -> sqlite3.Row:
    """Return the user row for valid credentials, else raise INVALID_CREDENTIALS (401)."""
    row = user_repo.find_by_username(conn, username)
    stored = row["password_hash"] if row is not None else _DUMMY_HASH  # same PBKDF2 work for unknown users (SEC-11)
    if not verify_password(password, stored) or row is None:
        raise AuthenticationError("invalid username or password", code="INVALID_CREDENTIALS")
    return row


def load_principal(conn: sqlite3.Connection, claims: TokenClaims) -> Principal:
    row = user_repo.find_principal_row(conn, claims.user_id)
    if row is None or row["role"] != claims.role:
        raise AuthenticationError("user no longer valid")
    return Principal(
        user_id=row["id"],
        username=row["username"],
        role=Role(row["role"]),
        display_name=row["display_name"],
        hospital_id=row["hospital_id"],
        hospital_code=row["hospital_code"],
        customer_id=row["customer_id"],
    )
