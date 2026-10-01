"""Typed domain errors. The API layer maps each class to an HTTP status and error envelope."""

from __future__ import annotations


class MediCardError(Exception):
    """Base error carrying a stable UPPER_SNAKE code and a human message."""

    status_hint = 400

    def __init__(self, code: str, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


class ValidationError(MediCardError):
    """Input is malformed or violates a field rule (422)."""

    status_hint = 422


class BusinessRuleError(MediCardError):
    """Input is well-formed but breaks a business rule (422)."""

    status_hint = 422


class AuthenticationError(MediCardError):
    """Missing, invalid or expired credentials (401)."""

    status_hint = 401

    def __init__(self, message: str = "authentication required", code: str = "UNAUTHENTICATED") -> None:
        super().__init__(code, message)


class AuthorizationError(MediCardError):
    """Authenticated but the role may not perform this action (403)."""

    status_hint = 403

    def __init__(self, message: str = "role not permitted for this action") -> None:
        super().__init__("FORBIDDEN", message)


class NotFoundError(MediCardError):
    """Entity does not exist or is not visible to the caller (404, NFR-04 isolation)."""

    status_hint = 404


class ConflictError(MediCardError):
    """Uniqueness or state conflict (409)."""

    status_hint = 409


class InvalidClaimStateException(ConflictError):  # noqa: N818 (name mandated by AC-08)
    """AC-08: a claim case transition not allowed by app_spec §6.2."""

    def __init__(self, current: str, target: str) -> None:
        super().__init__("INVALID_CLAIM_STATE", f"case cannot move from {current} to {target}")
        self.current = current
        self.target = target


class InvalidPreAuthStateException(ConflictError):  # noqa: N818 (mirrors AC-08 naming)
    """AC-04: a pre-auth transition not allowed by app_spec §6.1."""

    def __init__(self, current: str, target: str) -> None:
        super().__init__("INVALID_PREAUTH_STATE", f"pre-auth cannot move from {current} to {target}")
        self.current = current
        self.target = target


class SettlementInvariantError(MediCardError):
    """AC-07: the computed settlement broke 0 <= settlement <= admissible. Never persisted."""

    status_hint = 500

    def __init__(self, message: str) -> None:
        super().__init__("SETTLEMENT_INVARIANT_VIOLATED", message)
