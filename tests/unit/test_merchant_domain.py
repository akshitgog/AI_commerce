"""Unit tests for Merchant and MerchantUser domain entities.

No database, no ORM.  These tests verify:
1. Merchant membership can be represented safely.
2. Merchant A and Merchant B data are distinguishable by tenant ownership.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ai_commerce_gateway.domain.enums import MerchantRole, RecordStatus
from ai_commerce_gateway.domain.merchant import (
    VALID_MERCHANT_ROLES,
    AddMerchantUserDomain,
    CreateMerchantDomain,
    MerchantEntity,
    MerchantUserEntity,
    validate_merchant_name,
    validate_merchant_role,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _make_merchant(merchant_id: str = "mer_aaa", name: str = "Test Shop") -> MerchantEntity:
    now = _utc_now()
    return MerchantEntity(
        id=merchant_id,
        name=name,
        status=RecordStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def _make_user(
    merchant_id: str = "mer_aaa",
    user_id: str = "u_001",
    role: MerchantRole = MerchantRole.ADMIN,
) -> MerchantUserEntity:
    return MerchantUserEntity(
        id=f"musr_{merchant_id}_{user_id}",
        merchant_id=merchant_id,
        user_id=user_id,
        role=role,
        created_at=_utc_now(),
    )


# ---------------------------------------------------------------------------
# MerchantEntity tests
# ---------------------------------------------------------------------------


class TestMerchantEntity:
    def test_merchant_fields_are_accessible(self) -> None:
        m = _make_merchant("mer_abc", "Shop A")
        assert m.id == "mer_abc"
        assert m.name == "Shop A"
        assert m.status is RecordStatus.ACTIVE

    def test_merchant_is_frozen(self) -> None:
        m = _make_merchant()
        with pytest.raises((AttributeError, TypeError)):
            m.name = "changed"  # type: ignore[misc]

    def test_two_merchants_are_distinct(self) -> None:
        a = _make_merchant("mer_a", "Shop A")
        b = _make_merchant("mer_b", "Shop B")
        assert a.id != b.id
        assert a.name != b.name

    def test_merchant_create_domain_command(self) -> None:
        cmd = CreateMerchantDomain(
            id="mer_x",
            name="My Store",
            idempotency_key="idem_1",
        )
        assert cmd.id == "mer_x"
        assert cmd.status is RecordStatus.ACTIVE  # default


# ---------------------------------------------------------------------------
# MerchantUserEntity tests
# ---------------------------------------------------------------------------


class TestMerchantUserEntity:
    def test_user_belongs_to_own_merchant(self) -> None:
        user = _make_user(merchant_id="mer_a")
        assert user.belongs_to("mer_a") is True

    def test_user_does_not_belong_to_other_merchant(self) -> None:
        user = _make_user(merchant_id="mer_a")
        assert user.belongs_to("mer_b") is False  # ← tenant isolation

    def test_has_role_positive(self) -> None:
        user = _make_user(role=MerchantRole.ADMIN)
        assert user.has_role(MerchantRole.ADMIN) is True
        assert user.has_role(MerchantRole.ADMIN, MerchantRole.EDITOR) is True

    def test_has_role_negative(self) -> None:
        user = _make_user(role=MerchantRole.VIEWER)
        assert user.has_role(MerchantRole.ADMIN) is False

    def test_add_merchant_user_domain_command(self) -> None:
        cmd = AddMerchantUserDomain(
            id="musr_1",
            merchant_id="mer_a",
            user_id="u_42",
            role=MerchantRole.EDITOR,
        )
        assert cmd.role is MerchantRole.EDITOR

    def test_merchant_user_entity_is_frozen(self) -> None:
        user = _make_user()
        with pytest.raises((AttributeError, TypeError)):
            user.role = MerchantRole.VIEWER  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Tenant isolation between two merchants
# ---------------------------------------------------------------------------


class TestTenantSeparation:
    """Verify that domain objects correctly separate two merchant tenants."""

    def test_merchant_a_and_b_are_separate_objects(self) -> None:
        a = _make_merchant("mer_a", "Alpha")
        b = _make_merchant("mer_b", "Beta")
        assert a is not b
        assert a.id != b.id

    def test_user_of_a_is_not_member_of_b(self) -> None:
        user_a = _make_user(merchant_id="mer_a", user_id="u_1")
        assert user_a.belongs_to("mer_b") is False

    def test_different_users_in_different_merchants(self) -> None:
        user_a = _make_user(merchant_id="mer_a", user_id="u_alice")
        user_b = _make_user(merchant_id="mer_b", user_id="u_alice")
        # Same user_id, different merchant — they're separate entities
        assert user_a.merchant_id != user_b.merchant_id
        assert user_a.belongs_to("mer_a") is True
        assert user_b.belongs_to("mer_b") is True
        assert user_a.belongs_to("mer_b") is False


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


class TestValidationHelpers:
    def test_empty_name_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_merchant_name("")

    def test_whitespace_only_name_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_merchant_name("   ")

    def test_too_long_name_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_merchant_name("x" * 256)

    def test_valid_name_passes(self) -> None:
        validate_merchant_name("Good Name")  # must not raise

    def test_all_roles_are_valid(self) -> None:
        for role in MerchantRole:
            validate_merchant_role(role)  # must not raise

    def test_valid_merchant_roles_set_is_complete(self) -> None:
        assert VALID_MERCHANT_ROLES == frozenset(MerchantRole)
