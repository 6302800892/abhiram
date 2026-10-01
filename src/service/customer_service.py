"""AC-01: customer registration, policy linking and coverage view (EL-R1 .. EL-R3)."""

from __future__ import annotations

import logging
import re
import sqlite3

from src.domain.clock import Clock, iso
from src.domain.enums import Role
from src.domain.exceptions import BusinessRuleError, ConflictError, ValidationError
from src.domain.principal import Principal
from src.repository import hospital_repo, policy_repo, user_repo
from src.service import coverage_service
from src.service.auth_service import hash_password

logger = logging.getLogger("medicard.customer")
USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,39}$")


def register(
    conn: sqlite3.Connection, *, username: str, password: str, full_name: str, clock: Clock, iterations: int
) -> int:
    username = username.strip().lower()
    if not USERNAME_RE.match(username):
        raise ValidationError("INVALID_USERNAME", "username must be 3-40 chars: a-z, 0-9, '.', '_', '-'")
    if len(password) < 8:
        raise ValidationError("WEAK_PASSWORD", "password must be at least 8 characters")
    if not full_name.strip():
        raise ValidationError("FULL_NAME_REQUIRED", "full_name is required")
    if user_repo.find_by_username(conn, username) is not None:
        raise ConflictError("USERNAME_TAKEN", f"username {username} is already registered")
    now = iso(clock.now())
    with conn:
        user_id = user_repo.insert_user(
            conn, username=username, password_hash=hash_password(password, iterations=iterations),
            role=Role.CUSTOMER.value, display_name=full_name.strip(), created_at=now,
        )
        customer_id = user_repo.insert_customer(conn, user_id=user_id, full_name=full_name.strip(), created_at=now)
    logger.info("customer.registered", extra={"customer_id": customer_id})
    return customer_id


def link_policy(
    conn: sqlite3.Connection, principal: Principal, *, policy_number: str, member_id: str, date_of_birth: str
) -> dict[str, object]:
    """EL-R2: all three identifiers must match a member on the policy."""
    policy = policy_repo.find_policy(conn, policy_number)
    member = policy_repo.find_member(conn, member_id)
    if (
        policy is None
        or member is None
        or member["policy_id"] != policy["id"]
        or member["date_of_birth"] != date_of_birth
    ):
        raise BusinessRuleError("POLICY_LINK_MISMATCH", "policy number, member id and date of birth do not match")
    if member["customer_id"] is not None and member["customer_id"] != principal.customer_id:
        raise ConflictError("MEMBER_ALREADY_LINKED", "this member is already linked to another customer")
    assert principal.customer_id is not None
    with conn:
        policy_repo.link_member(conn, member["id"], principal.customer_id)
    logger.info("customer.policy_linked", extra={"customer_id": principal.customer_id})
    linked = policy_repo.find_member(conn, member_id)
    assert linked is not None
    return coverage_service.coverage_view(conn, linked)


def coverage(conn: sqlite3.Connection, principal: Principal) -> dict[str, object]:
    """EL-R3: every linked policy plus the in-network hospital list."""
    assert principal.customer_id is not None
    members = policy_repo.members_of_customer(conn, principal.customer_id)
    hospitals = hospital_repo.list_all(conn, in_network_only=True)
    return {
        "policies": [coverage_service.coverage_view(conn, m) for m in members],
        "network_hospitals": [{"code": h["code"], "name": h["name"], "city": h["city"]} for h in hospitals],
    }
