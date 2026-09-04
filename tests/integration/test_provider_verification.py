from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ai_commerce_gateway.application.provider_verification import (
    ProviderVerificationApplicationService,
)
from ai_commerce_gateway.contracts.models import (
    CreateProviderOrderCommand,
    HandleWebhookCommand,
    Money,
    ProviderLookupCommand,
    ProviderObservation,
    VerifyCheckoutCommand,
)
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.core.ids import EntityPrefix
from ai_commerce_gateway.domain.enums import ProviderName, TransactionState
from ai_commerce_gateway.domain.provider_verification import (
    ProviderEvidence,
    WebhookProcessingResult,
)
from ai_commerce_gateway.infrastructure.database import models
from ai_commerce_gateway.infrastructure.database.provider_verification import (
    SqlAlchemyVerificationUnitOfWork,
)

NOW = datetime(2026, 9, 4, 17, 0, tzinfo=UTC)
ORDER_ID = "order_database_123"
PAYMENT_ID = "pay_database_456"
SessionFactory = sessionmaker[Session]


class VerificationProvider:
    def __init__(self) -> None:
        self.payment_state = "captured"
        self.order_state = "paid"
        self.webhook_state = "captured"
        self.webhook_order_id: str | None = ORDER_ID
        self.webhook_payment_id: str | None = PAYMENT_ID
        self.checkout_calls = 0
        self.payment_lookup_calls = 0
        self.order_lookup_calls = 0
        self.webhook_calls = 0
        self.fail_lookup = False
        self.authenticity_verified = True
        self.amount = Money(amount_minor=50_000, currency="INR")

    def create_order(self, command: CreateProviderOrderCommand) -> ProviderObservation:
        raise AssertionError("B5 must not create an order")

    def verify_checkout(self, command: VerifyCheckoutCommand) -> ProviderEvidence:
        self.checkout_calls += 1
        return observation(
            order_id=command.provider_order_id,
            payment_id=command.provider_payment_id,
            authenticity_verified=self.authenticity_verified,
            source="checkout_signature",
        )

    def handle_webhook(self, command: HandleWebhookCommand) -> ProviderEvidence:
        self.webhook_calls += 1
        if self.webhook_order_id is None:
            return observation(source="ignored_webhook")
        return observation(
            order_id=self.webhook_order_id,
            payment_id=self.webhook_payment_id,
            payment_state=self.webhook_state,
            capture_state=("captured" if self.webhook_state == "captured" else "not_captured"),
            amount=self.amount,
            source=f"webhook:{self.webhook_state}",
        )

    def lookup_order(self, command: ProviderLookupCommand) -> ProviderEvidence:
        self.order_lookup_calls += 1
        if self.fail_lookup:
            raise RuntimeError("temporary lookup failure")
        return observation(
            order_id=command.provider_order_id,
            order_state=self.order_state,
            amount=self.amount,
            source="order_lookup",
        )

    def lookup_payment(self, command: ProviderLookupCommand) -> ProviderEvidence:
        self.payment_lookup_calls += 1
        if self.fail_lookup:
            raise RuntimeError("temporary lookup failure")
        return observation(
            order_id=command.provider_order_id,
            payment_id=command.provider_payment_id,
            payment_state=self.payment_state,
            capture_state=("captured" if self.payment_state == "captured" else "not_captured"),
            amount=self.amount,
            source="payment_lookup",
        )


def observation(
    *,
    order_id: str | None = None,
    payment_id: str | None = None,
    order_state: str | None = None,
    payment_state: str | None = None,
    capture_state: str | None = None,
    amount: Money | None = None,
    authenticity_verified: bool = True,
    source: str,
) -> ProviderEvidence:
    return ProviderEvidence(
        provider=ProviderName.RAZORPAY,
        provider_amount=amount,
        provider_order_id=order_id,
        provider_payment_id=payment_id,
        provider_order_state=order_state,
        provider_payment_state=payment_state,
        capture_state=capture_state,
        authenticity_verified=authenticity_verified,
        observed_at=NOW + timedelta(seconds=1),
        observation_source=source,
    )


@contextmanager
def verification_database(path: Path) -> Iterator[tuple[Engine, SessionFactory]]:
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    models.Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield engine, factory
    finally:
        engine.dispose()


def seed_payment_pending(factory: SessionFactory) -> None:
    with factory.begin() as session:
        session.add_all(
            [
                models.Merchant(id="mer_verify", name="Merchant", status="ACTIVE"),
                models.Buyer(
                    id="buy_verify", external_identity="verify@example.test", status="ACTIVE"
                ),
                models.Product(
                    id="prod_verify",
                    merchant_id="mer_verify",
                    sku="verify-sku",
                    title="Verified Product",
                    description="Verification fixture",
                    category=None,
                    price_minor=50_000,
                    currency="INR",
                    available_quantity=1,
                    status="PUBLISHED",
                    version=1,
                ),
                models.PurchaseProposal(
                    id="prop_verify",
                    buyer_id="buy_verify",
                    merchant_id="mer_verify",
                    product_id="prod_verify",
                    product_version=1,
                    quantity=1,
                    unit_price_minor=50_000,
                    total_minor=50_000,
                    currency="INR",
                    proposal_hash="sha256:verify",
                    status="PROPOSED",
                    expires_at=NOW + timedelta(minutes=10),
                ),
                models.Transaction(
                    id="txn_verify",
                    proposal_id="prop_verify",
                    buyer_authorization_id=None,
                    merchant_decision_id=None,
                    merchant_id="mer_verify",
                    buyer_id="buy_verify",
                    amount_minor=50_000,
                    currency="INR",
                    state=TransactionState.PAYMENT_PENDING.value,
                    created_at=NOW,
                    updated_at=NOW,
                ),
                models.PaymentAttempt(
                    id="pay_attempt_verify",
                    transaction_id="txn_verify",
                    attempt_number=1,
                    provider=ProviderName.RAZORPAY.value,
                    provider_request_fingerprint="sha256:request",
                    provider_order_id=ORDER_ID,
                    provider_payment_id=None,
                    provider_order_state="created",
                    provider_payment_state=None,
                    capture_state=None,
                    last_verified_at=None,
                    created_at=NOW,
                    updated_at=NOW,
                ),
            ]
        )


def service(
    factory: SessionFactory, provider: VerificationProvider
) -> ProviderVerificationApplicationService:
    def ids(prefix: EntityPrefix) -> str:
        return f"{prefix}_{uuid4().hex}"

    return ProviderVerificationApplicationService(
        lambda: SqlAlchemyVerificationUnitOfWork(factory, clock=lambda: NOW),
        provider,
        clock=lambda: NOW,
        id_factory=ids,
    )


def checkout_command(
    *, order_id: str = ORDER_ID, payment_id: str = PAYMENT_ID
) -> VerifyCheckoutCommand:
    return VerifyCheckoutCommand(
        transaction_id="txn_verify",
        provider_order_id=order_id,
        provider_payment_id=payment_id,
        signature="a" * 64,
    )


def webhook_command(event_id: str, raw_body: bytes | None = None) -> HandleWebhookCommand:
    return HandleWebhookCommand(
        raw_body=raw_body or f'{{"event":"{event_id}"}}'.encode(),
        signature="b" * 64,
    )


def deliver_webhook(
    verification: ProviderVerificationApplicationService,
    event_id: str,
    *,
    correlation_id: str,
    raw_body: bytes | None = None,
) -> WebhookProcessingResult:
    return verification.handle_webhook(
        webhook_command(event_id, raw_body),
        provider_event_id=event_id,
        correlation_id=correlation_id,
    )


def test_checkout_captured_lookup_reaches_success_with_two_causal_events(tmp_path: Path) -> None:
    provider = VerificationProvider()
    with verification_database(tmp_path / "captured.db") as (_, factory):
        seed_payment_pending(factory)
        result = service(factory, provider).verify_checkout(
            checkout_command(), correlation_id="corr_checkout"
        )

        assert result.state is TransactionState.SUCCEEDED
        assert result.provider_phase is not None
        assert result.provider_phase.order_state == "paid"
        assert result.provider_phase.payment_state == "captured"
        assert result.provider_phase.capture_state == "captured"
        with factory() as session:
            transitions = list(
                session.scalars(
                    select(models.TransactionEvent).order_by(models.TransactionEvent.created_at)
                )
            )
            attempt = session.get(models.PaymentAttempt, "pay_attempt_verify")
        assert [(event.previous_state, event.new_state) for event in transitions] == [
            ("PAYMENT_PENDING", "VERIFYING"),
            ("VERIFYING", "SUCCEEDED"),
        ]
        assert all(event.provider_reference_redacted == "..._456" for event in transitions)
        assert attempt is not None
        assert attempt.provider_payment_id == PAYMENT_ID
        assert attempt.last_verified_at is not None


def test_checkout_authorized_remains_verifying(tmp_path: Path) -> None:
    provider = VerificationProvider()
    provider.payment_state = "authorized"
    provider.order_state = "attempted"
    with verification_database(tmp_path / "authorized.db") as (_, factory):
        seed_payment_pending(factory)
        result = service(factory, provider).verify_checkout(
            checkout_command(), correlation_id="corr_checkout"
        )

        assert result.state is TransactionState.VERIFYING
        assert result.state is not TransactionState.SUCCEEDED


def test_checkout_rejects_client_order_mismatch_before_provider(tmp_path: Path) -> None:
    provider = VerificationProvider()
    with verification_database(tmp_path / "mismatch.db") as (_, factory):
        seed_payment_pending(factory)
        with pytest.raises(AppError) as captured:
            service(factory, provider).verify_checkout(
                checkout_command(order_id="order_other"), correlation_id="corr_checkout"
            )

    assert captured.value.code is ErrorCode.PROVIDER_ERROR
    assert provider.checkout_calls == 0


def test_checkout_rejects_provider_money_mismatch_without_state_change(
    tmp_path: Path,
) -> None:
    provider = VerificationProvider()
    provider.amount = Money(amount_minor=49_999, currency="INR")
    with verification_database(tmp_path / "amount_mismatch.db") as (_, factory):
        seed_payment_pending(factory)
        with pytest.raises(AppError) as captured:
            service(factory, provider).verify_checkout(
                checkout_command(), correlation_id="corr_checkout"
            )
        with factory() as session:
            transaction = session.get(models.Transaction, "txn_verify")
            event_count = session.scalar(select(func.count()).select_from(models.TransactionEvent))

    assert captured.value.code is ErrorCode.PROVIDER_ERROR
    assert transaction is not None
    assert transaction.state == TransactionState.PAYMENT_PENDING.value
    assert event_count == 0


def test_successful_checkout_replay_still_requires_authentic_signature(tmp_path: Path) -> None:
    provider = VerificationProvider()
    with verification_database(tmp_path / "success_replay.db") as (_, factory):
        seed_payment_pending(factory)
        verification = service(factory, provider)
        verification.verify_checkout(checkout_command(), correlation_id="corr_first")
        provider.authenticity_verified = False

        with pytest.raises(AppError) as captured:
            verification.verify_checkout(checkout_command(), correlation_id="corr_replay")

    assert captured.value.code is ErrorCode.PROVIDER_ERROR
    assert provider.checkout_calls == 2
    assert provider.payment_lookup_calls == 1
    assert provider.order_lookup_calls == 1


@pytest.mark.parametrize("event_id", ["", " ", "e" * 256])
def test_webhook_rejects_invalid_transport_event_id_before_provider(
    tmp_path: Path, event_id: str
) -> None:
    provider = VerificationProvider()
    with verification_database(tmp_path / f"invalid_event_{len(event_id)}.db") as (_, factory):
        seed_payment_pending(factory)
        with pytest.raises(AppError) as captured:
            service(factory, provider).handle_webhook(
                webhook_command("payload_event"),
                provider_event_id=event_id,
                correlation_id="corr_invalid_event",
            )

    assert captured.value.code is ErrorCode.PROVIDER_ERROR
    assert provider.webhook_calls == 0


def test_captured_webhook_is_deduplicated_durably(tmp_path: Path) -> None:
    provider = VerificationProvider()
    with verification_database(tmp_path / "duplicate.db") as (_, factory):
        seed_payment_pending(factory)
        verification = service(factory, provider)
        first = deliver_webhook(verification, "event_captured", correlation_id="corr_webhook")
        second = deliver_webhook(
            verification, "event_captured", correlation_id="corr_webhook_retry"
        )

        assert first.processing_status == "PROCESSED"
        assert first.transaction_state is TransactionState.SUCCEEDED
        assert second.duplicate is True
        assert second.transaction_state is TransactionState.SUCCEEDED
        assert provider.payment_lookup_calls == 1
        assert provider.order_lookup_calls == 1
        with factory() as session:
            assert session.scalar(select(func.count()).select_from(models.ProviderWebhook)) == 1
            assert session.scalar(select(func.count()).select_from(models.TransactionEvent)) == 2


def test_same_event_id_with_different_payload_is_rejected(tmp_path: Path) -> None:
    provider = VerificationProvider()
    with verification_database(tmp_path / "reuse.db") as (_, factory):
        seed_payment_pending(factory)
        verification = service(factory, provider)
        deliver_webhook(
            verification,
            "event_reused",
            correlation_id="corr_webhook",
            raw_body=b'{"sequence":1}',
        )
        with pytest.raises(AppError) as captured:
            deliver_webhook(
                verification,
                "event_reused",
                correlation_id="corr_webhook",
                raw_body=b'{"sequence":2}',
            )
    assert captured.value.code is ErrorCode.PROVIDER_ERROR


def test_failed_then_captured_webhook_does_not_terminally_fail_order(tmp_path: Path) -> None:
    provider = VerificationProvider()
    provider.webhook_state = "failed"
    with verification_database(tmp_path / "out_of_order.db") as (_, factory):
        seed_payment_pending(factory)
        verification = service(factory, provider)
        failed = deliver_webhook(verification, "event_failed", correlation_id="corr_failed")
        assert failed.transaction_state is TransactionState.PAYMENT_PENDING

        provider.webhook_state = "captured"
        captured = deliver_webhook(verification, "event_captured", correlation_id="corr_captured")
        assert captured.transaction_state is TransactionState.SUCCEEDED


def test_authorized_webhook_after_success_cannot_downgrade(tmp_path: Path) -> None:
    provider = VerificationProvider()
    with verification_database(tmp_path / "no_downgrade.db") as (_, factory):
        seed_payment_pending(factory)
        verification = service(factory, provider)
        deliver_webhook(verification, "event_captured", correlation_id="corr_captured")
        provider.webhook_state = "authorized"
        result = deliver_webhook(verification, "event_authorized", correlation_id="corr_authorized")
        assert result.transaction_state is TransactionState.SUCCEEDED
        with factory() as session:
            assert session.scalar(select(func.count()).select_from(models.TransactionEvent)) == 2


def test_ignored_and_orphan_webhooks_are_recorded_without_state_change(tmp_path: Path) -> None:
    provider = VerificationProvider()
    provider.webhook_order_id = None
    with verification_database(tmp_path / "ignored.db") as (_, factory):
        seed_payment_pending(factory)
        ignored = deliver_webhook(
            service(factory, provider), "event_ignored", correlation_id="corr_ignored"
        )
        assert ignored.processing_status == "IGNORED"

        provider.webhook_order_id = "order_unknown"
        orphan = deliver_webhook(
            service(factory, provider), "event_orphan", correlation_id="corr_orphan"
        )
        assert orphan.processing_status == "ORPHAN"
        with factory() as session:
            transaction = session.get(models.Transaction, "txn_verify")
        assert transaction is not None
        assert transaction.state == TransactionState.PAYMENT_PENDING.value


def test_lookup_failure_leaves_receipt_resumable_on_duplicate(tmp_path: Path) -> None:
    provider = VerificationProvider()
    provider.fail_lookup = True
    with verification_database(tmp_path / "resume.db") as (_, factory):
        seed_payment_pending(factory)
        verification = service(factory, provider)
        command = webhook_command("event_resume")
        with pytest.raises(RuntimeError, match="lookup failure"):
            verification.handle_webhook(
                command,
                provider_event_id="event_resume",
                correlation_id="corr_first",
            )
        with factory() as session:
            receipt = session.scalar(select(models.ProviderWebhook))
        assert receipt is not None
        assert receipt.processing_status == "RECEIVED"

        provider.fail_lookup = False
        result = verification.handle_webhook(
            command,
            provider_event_id="event_resume",
            correlation_id="corr_retry",
        )
        assert result.duplicate is True
        assert result.transaction_state is TransactionState.SUCCEEDED
        with factory() as session:
            assert session.scalar(select(func.count()).select_from(models.ProviderWebhook)) == 1
