from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta

import pytest

from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.domain.enums import (
    MerchantDecisionValue,
    NextRequiredGate,
    PolicyMode,
    ProductStatus,
)
from ai_commerce_gateway.domain.proposal_gates import (
    BuyerAuthorization,
    MerchantDecision,
    MerchantPolicySnapshot,
    PurchaseProposal,
    TrustedProductSnapshot,
    create_purchase_proposal,
    determine_next_gate,
    evaluate_merchant_policy,
    record_manual_merchant_decision,
    request_buyer_authorization,
    require_current_product,
)

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)


def product(**changes: object) -> TrustedProductSnapshot:
    values: dict[str, object] = {
        "id": "prod_test",
        "merchant_id": "mer_test",
        "version": 3,
        "price_minor": 50_000,
        "currency": "INR",
        "available_quantity": 5,
        "status": ProductStatus.PUBLISHED,
    }
    values.update(changes)
    return TrustedProductSnapshot(**values)  # type: ignore[arg-type]


def proposal(
    *, product_snapshot: TrustedProductSnapshot | None = None, proposal_id: str = "prop_test"
) -> PurchaseProposal:
    return create_purchase_proposal(
        proposal_id=proposal_id,
        buyer_id="buy_test",
        requested_merchant_id="mer_test",
        product=product_snapshot or product(),
        quantity=2,
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=15),
    )


def approved_authorization(
    purchase_proposal: PurchaseProposal | None = None,
) -> BuyerAuthorization:
    purchase_proposal = purchase_proposal or proposal()
    requested = request_buyer_authorization(
        authorization_id="auth_test",
        proposal=purchase_proposal,
        requested_at=NOW,
    )
    return requested.approve(
        purchase_proposal,
        proposal_hash=purchase_proposal.proposal_hash,
        max_quantity=purchase_proposal.quantity,
        max_amount_minor=purchase_proposal.total_minor,
        currency=purchase_proposal.currency,
        expires_at=purchase_proposal.expires_at,
        authorized_by="human:buy_test",
        now=NOW,
    )


def decision(
    value: MerchantDecisionValue,
    purchase_proposal: PurchaseProposal | None = None,
) -> MerchantDecision:
    purchase_proposal = purchase_proposal or proposal()
    return MerchantDecision(
        id="mdec_test",
        proposal_id=purchase_proposal.id,
        merchant_id=purchase_proposal.merchant_id,
        policy_id="pol_test",
        policy_version=1,
        decision=value,
        reason_code="TEST_DECISION",
        decided_by="policy:pol_test:v1",
        expires_at=purchase_proposal.expires_at,
        created_at=NOW,
    )


def test_proposal_hash_is_stable_for_the_same_commercial_snapshot() -> None:
    first = proposal(proposal_id="prop_first")
    second = proposal(proposal_id="prop_second")
    assert first.proposal_hash == second.proposal_hash
    assert first.proposal_hash.startswith("sha256:")


@pytest.mark.parametrize(
    "changed_product",
    [
        product(version=4),
        product(price_minor=50_001),
        product(currency="USD"),
    ],
)
def test_changed_commercial_product_snapshot_changes_the_hash(
    changed_product: TrustedProductSnapshot,
) -> None:
    assert proposal(product_snapshot=changed_product).proposal_hash != proposal().proposal_hash


def test_proposal_total_comes_from_the_trusted_product_and_snapshot_is_immutable() -> None:
    source = product(price_minor=12_345)
    created = proposal(product_snapshot=source)
    changed_source = replace(source, price_minor=99_999)

    assert created.unit_price_minor == 12_345
    assert created.total_minor == 24_690
    assert changed_source.price_minor == 99_999
    assert created.unit_price_minor == 12_345
    with pytest.raises(FrozenInstanceError):
        created.total_minor = 1  # type: ignore[misc]


def test_proposal_rejects_unpublished_wrong_merchant_and_unavailable_quantity() -> None:
    with pytest.raises(AppError) as unpublished:
        proposal(product_snapshot=product(status=ProductStatus.DRAFT))
    assert unpublished.value.code is ErrorCode.PRODUCT_UNAVAILABLE

    with pytest.raises(AppError) as wrong_merchant:
        create_purchase_proposal(
            proposal_id="prop_test",
            buyer_id="buy_test",
            requested_merchant_id="mer_other",
            product=product(),
            quantity=1,
            created_at=NOW,
            expires_at=NOW + timedelta(minutes=15),
        )
    assert wrong_merchant.value.code is ErrorCode.NOT_FOUND

    with pytest.raises(AppError) as unavailable:
        create_purchase_proposal(
            proposal_id="prop_test",
            buyer_id="buy_test",
            requested_merchant_id="mer_test",
            product=product(available_quantity=1),
            quantity=2,
            created_at=NOW,
            expires_at=NOW + timedelta(minutes=15),
        )
    assert unavailable.value.code is ErrorCode.PRODUCT_UNAVAILABLE


@pytest.mark.parametrize(
    ("field_name", "value", "reason"),
    [
        ("buyer_id", "buy_other", "buyer_mismatch"),
        ("proposal_id", "prop_other", "proposal_mismatch"),
        ("proposal_hash", "sha256:other", "proposal_hash_mismatch"),
        ("merchant_id", "mer_other", "merchant_mismatch"),
        ("product_id", "prod_other", "product_mismatch"),
        ("max_quantity", 1, "quantity_mismatch"),
        ("max_amount_minor", 1, "amount_mismatch"),
        ("currency", "USD", "currency_mismatch"),
        ("expires_at", NOW, "authorization_expired"),
    ],
)
def test_authorization_matching_rejects_every_scope_mismatch(
    field_name: str, value: object, reason: str
) -> None:
    authorization = replace(approved_authorization(), **{field_name: value})
    with pytest.raises(AppError) as error:
        authorization.require_matches(proposal(), now=NOW)
    assert error.value.code is ErrorCode.AUTHORIZATION_INVALID
    assert error.value.details["reason"] == reason


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"max_quantity": 1}, "quantity_mismatch"),
        ({"max_quantity": 3}, "quantity_mismatch"),
        ({"max_amount_minor": 99_999}, "amount_mismatch"),
        ({"max_amount_minor": 100_001}, "amount_mismatch"),
        ({"currency": "USD"}, "currency_mismatch"),
        ({"expires_at": NOW}, "expiry_out_of_scope"),
        ({"expires_at": NOW + timedelta(minutes=16)}, "expiry_out_of_scope"),
    ],
)
def test_buyer_approval_cannot_expand_or_change_proposal_scope(
    changes: dict[str, object], reason: str
) -> None:
    purchase_proposal = proposal()
    requested = request_buyer_authorization(
        authorization_id="auth_test", proposal=purchase_proposal, requested_at=NOW
    )
    arguments: dict[str, object] = {
        "proposal_hash": purchase_proposal.proposal_hash,
        "max_quantity": purchase_proposal.quantity,
        "max_amount_minor": purchase_proposal.total_minor,
        "currency": purchase_proposal.currency,
        "expires_at": purchase_proposal.expires_at,
        "authorized_by": "human:buy_test",
        "now": NOW,
    }
    arguments.update(changes)
    with pytest.raises(AppError) as error:
        requested.approve(purchase_proposal, **arguments)  # type: ignore[arg-type]
    assert error.value.code is ErrorCode.AUTHORIZATION_INVALID
    assert error.value.details["reason"] == reason


def test_buyer_and_merchant_gates_are_independent() -> None:
    purchase_proposal = proposal()
    authorization = approved_authorization(purchase_proposal)

    assert (
        determine_next_gate(purchase_proposal, None, decision(MerchantDecisionValue.ALLOW), now=NOW)
        is NextRequiredGate.BUYER_AUTH_REQUIRED
    )
    assert (
        determine_next_gate(purchase_proposal, authorization, None, now=NOW)
        is NextRequiredGate.MERCHANT_POLICY_PENDING
    )
    assert (
        determine_next_gate(
            purchase_proposal,
            authorization,
            decision(MerchantDecisionValue.REVIEW_REQUIRED),
            now=NOW,
        )
        is NextRequiredGate.MERCHANT_REVIEW_REQUIRED
    )
    assert (
        determine_next_gate(
            purchase_proposal,
            authorization,
            decision(MerchantDecisionValue.ALLOW),
            now=NOW,
        )
        is NextRequiredGate.READY
    )


@pytest.mark.parametrize(
    ("mode", "limit", "currency", "expected"),
    [
        (PolicyMode.DENY_ALL, None, None, MerchantDecisionValue.DENY),
        (PolicyMode.MANUAL_ALL, None, None, MerchantDecisionValue.REVIEW_REQUIRED),
        (PolicyMode.AUTO_BELOW_LIMIT, 100_000, "INR", MerchantDecisionValue.ALLOW),
        (PolicyMode.AUTO_BELOW_LIMIT, 99_999, "INR", MerchantDecisionValue.REVIEW_REQUIRED),
        (PolicyMode.AUTO_BELOW_LIMIT, 100_000, "USD", MerchantDecisionValue.REVIEW_REQUIRED),
    ],
)
def test_merchant_policy_modes_are_deterministic(
    mode: PolicyMode,
    limit: int | None,
    currency: str | None,
    expected: MerchantDecisionValue,
) -> None:
    purchase_proposal = proposal()
    policy = MerchantPolicySnapshot(
        id="pol_test",
        merchant_id="mer_test",
        mode=mode,
        auto_accept_max_minor=limit,
        currency=currency,
        version=1,
    )
    result = evaluate_merchant_policy(
        decision_id="mdec_test",
        proposal=purchase_proposal,
        policy=policy,
        decided_at=NOW,
    )
    assert result.decision is expected
    assert result.policy_version == 1


def test_manual_decision_requires_review_and_stays_within_proposal_expiry() -> None:
    purchase_proposal = proposal()
    review = decision(MerchantDecisionValue.REVIEW_REQUIRED, purchase_proposal)
    allowed = record_manual_merchant_decision(
        decision_id="mdec_manual",
        proposal=purchase_proposal,
        review_decision=review,
        decision=MerchantDecisionValue.ALLOW,
        reason_code="MERCHANT_APPROVED",
        decided_by="merchant_user",
        expires_at=None,
        decided_at=NOW,
    )
    assert allowed.decision is MerchantDecisionValue.ALLOW
    assert allowed.policy_id == review.policy_id
    assert allowed.expires_at == purchase_proposal.expires_at

    with pytest.raises(AppError) as error:
        record_manual_merchant_decision(
            decision_id="mdec_invalid",
            proposal=purchase_proposal,
            review_decision=allowed,
            decision=MerchantDecisionValue.ALLOW,
            reason_code="MERCHANT_APPROVED",
            decided_by="merchant_user",
            expires_at=None,
            decided_at=NOW,
        )
    assert error.value.code is ErrorCode.INVALID_STATE


@pytest.mark.parametrize(
    "changed_product",
    [
        product(version=4),
        product(price_minor=50_001),
        product(currency="USD"),
        product(available_quantity=1),
        product(status=ProductStatus.UNPUBLISHED),
        product(merchant_id="mer_other"),
        product(id="prod_other"),
    ],
)
def test_readiness_rejects_current_product_drift(
    changed_product: TrustedProductSnapshot,
) -> None:
    with pytest.raises(AppError) as error:
        require_current_product(proposal(), changed_product)
    assert error.value.code is ErrorCode.PROPOSAL_STALE


@pytest.mark.parametrize(
    "changes",
    [
        {"version": 0},
        {"price_minor": -1},
        {"price_minor": 1.5},
        {"currency": "inr"},
        {"available_quantity": -1},
    ],
)
def test_trusted_product_snapshot_rejects_invalid_commercial_values(
    changes: dict[str, object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        product(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"quantity": 0},
        {"product_version": 0},
        {"total_minor": 1},
        {"expires_at": NOW},
        {"proposal_hash": "sha256:tampered"},
        {"expires_at": NOW.replace(tzinfo=None)},
    ],
)
def test_proposal_rejects_invalid_or_tampered_snapshot_fields(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        replace(proposal(), **changes)


def test_expired_proposal_is_rejected() -> None:
    with pytest.raises(AppError) as error:
        proposal().require_active(NOW + timedelta(minutes=15))
    assert error.value.code is ErrorCode.PROPOSAL_STALE


def test_approval_requires_requested_state_matching_hash_and_human_principal() -> None:
    purchase_proposal = proposal()
    requested = request_buyer_authorization(
        authorization_id="auth_test", proposal=purchase_proposal, requested_at=NOW
    )
    common = {
        "proposal": purchase_proposal,
        "proposal_hash": purchase_proposal.proposal_hash,
        "max_quantity": purchase_proposal.quantity,
        "max_amount_minor": purchase_proposal.total_minor,
        "currency": purchase_proposal.currency,
        "expires_at": purchase_proposal.expires_at,
        "authorized_by": "human:buy_test",
        "now": NOW,
    }
    with pytest.raises(AppError) as already_approved:
        approved_authorization().approve(**common)
    assert already_approved.value.details["reason"] == "authorization_not_requested"
    with pytest.raises(AppError) as wrong_hash:
        requested.approve(**(common | {"proposal_hash": "sha256:wrong"}))
    assert wrong_hash.value.details["reason"] == "proposal_hash_mismatch"
    with pytest.raises(AppError) as no_human:
        requested.approve(**(common | {"authorized_by": " "}))
    assert no_human.value.details["reason"] == "human_approver_missing"


@pytest.mark.parametrize(
    "changes",
    [
        {"version": 0},
        {"mode": PolicyMode.AUTO_BELOW_LIMIT, "auto_accept_max_minor": None, "currency": None},
        {"mode": PolicyMode.MANUAL_ALL, "auto_accept_max_minor": 1, "currency": "INR"},
    ],
)
def test_merchant_policy_snapshot_rejects_invalid_configuration(
    changes: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "id": "pol_test",
        "merchant_id": "mer_test",
        "mode": PolicyMode.MANUAL_ALL,
        "auto_accept_max_minor": None,
        "currency": None,
        "version": 1,
    }
    values.update(changes)
    with pytest.raises(ValueError):
        MerchantPolicySnapshot(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "changes",
    [
        {"proposal_id": "prop_other"},
        {"merchant_id": "mer_other"},
        {"expires_at": NOW},
    ],
)
def test_merchant_decision_matching_rejects_wrong_or_expired_scope(
    changes: dict[str, object],
) -> None:
    with pytest.raises(AppError) as error:
        replace(decision(MerchantDecisionValue.ALLOW), **changes).require_matches(
            proposal(), now=NOW
        )
    assert error.value.code is ErrorCode.POLICY_DENIED


def test_policy_cannot_decide_for_another_merchant() -> None:
    with pytest.raises(AppError) as error:
        evaluate_merchant_policy(
            decision_id="mdec_test",
            proposal=proposal(),
            policy=MerchantPolicySnapshot(
                id="pol_other",
                merchant_id="mer_other",
                mode=PolicyMode.MANUAL_ALL,
                auto_accept_max_minor=None,
                currency=None,
                version=1,
            ),
            decided_at=NOW,
        )
    assert error.value.code is ErrorCode.FORBIDDEN


@pytest.mark.parametrize(
    "changes",
    [
        {"decision": MerchantDecisionValue.REVIEW_REQUIRED},
        {"reason_code": " "},
        {"expires_at": NOW},
        {"expires_at": NOW + timedelta(minutes=16)},
    ],
)
def test_manual_merchant_decision_rejects_invalid_input(
    changes: dict[str, object],
) -> None:
    purchase_proposal = proposal()
    arguments: dict[str, object] = {
        "decision_id": "mdec_manual",
        "proposal": purchase_proposal,
        "review_decision": decision(MerchantDecisionValue.REVIEW_REQUIRED, purchase_proposal),
        "decision": MerchantDecisionValue.ALLOW,
        "reason_code": "MERCHANT_APPROVED",
        "decided_by": "merchant_user",
        "expires_at": None,
        "decided_at": NOW,
    }
    arguments.update(changes)
    with pytest.raises(AppError) as error:
        record_manual_merchant_decision(**arguments)  # type: ignore[arg-type]
    assert error.value.code is ErrorCode.VALIDATION_ERROR


def test_deny_decision_has_no_ready_gate() -> None:
    with pytest.raises(AppError) as error:
        determine_next_gate(
            proposal(),
            approved_authorization(),
            decision(MerchantDecisionValue.DENY),
            now=NOW,
        )
    assert error.value.code is ErrorCode.POLICY_DENIED
