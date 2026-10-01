"""The authenticated caller, resolved at the controller boundary (NFR-04)."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.enums import Role


@dataclass(frozen=True)
class Principal:
    user_id: int
    username: str
    role: Role
    display_name: str
    hospital_id: int | None = None
    hospital_code: str | None = None
    customer_id: int | None = None

    def is_staff(self) -> bool:
        """Insurer-side users see every case."""
        return self.role in (Role.INSURER, Role.ADMIN)
