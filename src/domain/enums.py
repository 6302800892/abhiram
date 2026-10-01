"""Enumerations shared across layers (string-valued so they serialise cleanly)."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    CUSTOMER = "CUSTOMER"
    HOSPITAL = "HOSPITAL"
    INSURER = "INSURER"
    ADMIN = "ADMIN"


class PolicyStatus(StrEnum):
    ACTIVE = "ACTIVE"
    LAPSED = "LAPSED"
    CANCELLED = "CANCELLED"


class EligibilityStatus(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"


class PreAuthStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    PARTIALLY_APPROVED = "PARTIALLY_APPROVED"
    REJECTED = "REJECTED"
    QUERY_RAISED = "QUERY_RAISED"


class CaseStatus(StrEnum):
    PRE_AUTH = "PRE_AUTH"
    ADMITTED = "ADMITTED"
    DISCHARGED = "DISCHARGED"
    SETTLED = "SETTLED"
    DISPUTED = "DISPUTED"
    CLOSED = "CLOSED"


SYSTEM_ACTOR = "SYSTEM"
