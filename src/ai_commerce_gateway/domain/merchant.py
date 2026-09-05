"""Merchant and MerchantUser domain entities.

Pure-Python value objects; they carry no SQLAlchemy state and may be
constructed / compared in tests without a database connection.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ai_commerce_gateway.domain.enums import MerchantRole, RecordStatus


@dataclass(frozen=True, slots=True)
class MerchantEntity:
    """Read-only snapshot of a Merchant record."""

    id: str
    name: str
    status: RecordStatus
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class MerchantUserEntity:
    """Read-only snapshot of a MerchantUser membership record."""

    id: str
    merchant_id: str
    user_id: str
    role: MerchantRole
    created_at: datetime

    def belongs_to(self, merchant_id: str) -> bool:
        return self.merchant_id == merchant_id

    def has_role(self, *roles: MerchantRole) -> bool:
        return self.role in roles


@dataclass(frozen=True, slots=True)
class CreateMerchantDomain:
    """Command for creating a Merchant at the domain layer."""

    id: str
    name: str
    idempotency_key: str
    status: RecordStatus = RecordStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class AddMerchantUserDomain:
    """Command for adding a MerchantUser membership at the domain layer."""

    id: str
    merchant_id: str
    user_id: str
    role: MerchantRole


# Membership validation helpers — kept in domain, not ORM


def validate_merchant_name(name: str) -> None:
    if not name or not name.strip():
        raise ValueError("Merchant name must not be empty.")
    if len(name) > 255:
        raise ValueError("Merchant name must be ≤ 255 characters.")


VALID_MERCHANT_ROLES: frozenset[MerchantRole] = frozenset(MerchantRole)


def validate_merchant_role(role: MerchantRole) -> None:
    if role not in VALID_MERCHANT_ROLES:
        raise ValueError(f"Invalid merchant role: {role!r}")
