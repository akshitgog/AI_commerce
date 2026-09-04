import json
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event, Lock
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ai_commerce_gateway.application.proposal_gates import (
    AuthorizationApplicationService,
    HumanBuyerApprovalVerifier,
    MerchantGateApplicationService,
    ProposalApplicationService,
    TransactionCreationApplicationService,
)
from ai_commerce_gateway.application.transaction_execution import (
    TransactionExecutionApplicationService,
)
from ai_commerce_gateway.contracts.models import (
    ActorContext,
    ApproveAuthorizationCommand,
    CreateProposalCommand,
    CreateProviderOrderCommand,
    CreateTransactionCommand,
    EvaluateMerchantPolicyCommand,
    ExecuteTransactionCommand,
    ProviderObservation,
    RequestAuthorizationCommand,
)
from ai_commerce_gateway.core.config import get_settings
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.domain.enums import (
    ActorType,
    AuthorizationStatus,
    PolicyMode,
    ProductStatus,
    ProviderName,
    TransactionState,
)
from ai_commerce_gateway.infrastructure.database import models
from ai_commerce_gateway.infrastructure.database.execution import (
    SqlAlchemyExecutionUnitOfWork,
)
from ai_commerce_gateway.infrastructure.database.proposal_gates import (
    SqlAlchemyProposalGateRepository,
)
from ai_commerce_gateway.providers.razorpay import RazorpayAdapter

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
SessionFactory = sessionmaker[Session]


class AllowHumanApproval(HumanBuyerApprovalVerifier):
    def verify(self, *, actor: ActorContext, buyer_id: str) -> str:
        return f"human-session:{buyer_id}"


class RecordingProvider:
    def __init__(
        self,
        *,
        before_response: Callable[[CreateProviderOrderCommand], None] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.commands: list[CreateProviderOrderCommand] = []
        self._before_response = before_response
        self._error = error
        self._lock = Lock()

    @property
    def call_count(self) -> int:
        with self._lock:
            return len(self.commands)

    def create_order(self, command: CreateProviderOrderCommand) -> ProviderObservation:
        with self._lock:
            self.commands.append(command)
        if self._before_response is not None:
            self._before_response(command)
        if self._error is not None:
            raise self._error
        return ProviderObservation(
            provider=ProviderName.RAZORPAY,
            provider_order_id="order_test_1234",
            provider_order_state="created",
            authenticity_verified=True,
            observed_at=NOW + timedelta(seconds=1),
            observation_source="create_order_response",
        )


class CrashingProvider(RecordingProvider):
    def create_order(self, command: CreateProviderOrderCommand) -> ProviderObservation:
        with self._lock:
            self.commands.append(command)
        raise KeyboardInterrupt("simulated process death")


class IncompleteObservationProvider(RecordingProvider):
    def create_order(self, command: CreateProviderOrderCommand) -> ProviderObservation:
        with self._lock:
            self.commands.append(command)
        return ProviderObservation(
            provider=ProviderName.RAZORPAY,
            provider_order_id=None,
            provider_order_state=None,
            authenticity_verified=False,
            observed_at=NOW,
            observation_source="incomplete_create_order_response",
        )


def actor(buyer_id: str = "buy_test") -> ActorContext:
    return ActorContext(
        actor_id=buyer_id,
        actor_type=ActorType.BUYER,
        correlation_id="corr_execute_test",
    )


@contextmanager
def execution_database(path: Path) -> Iterator[tuple[Engine, SessionFactory]]:
    engine = create_engine(
        f"sqlite:///{path.as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    models.Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield engine, factory
    finally:
        engine.dispose()


def seed_ready_transaction(factory: SessionFactory) -> str:
    with factory.begin() as session:
        session.add_all(
            [
                models.Merchant(id="mer_test", name="Merchant", status="ACTIVE"),
                models.Buyer(id="buy_test", external_identity="buyer@test", status="ACTIVE"),
                models.Buyer(id="buy_other", external_identity="other@test", status="ACTIVE"),
                models.Product(
                    id="prod_test",
                    merchant_id="mer_test",
                    sku="sku-test",
                    title="Trusted Product",
                    description="Database-backed fixture",
                    category=None,
                    price_minor=50_000,
                    currency="INR",
                    available_quantity=5,
                    status=ProductStatus.PUBLISHED.value,
                    version=3,
                ),
                models.MerchantPolicy(
                    id="pol_test",
                    merchant_id="mer_test",
                    mode=PolicyMode.AUTO_BELOW_LIMIT.value,
                    auto_accept_max_minor=200_000,
                    currency="INR",
                    version=1,
                    status="ACTIVE",
                ),
            ]
        )

    with factory.begin() as session:
        repository = SqlAlchemyProposalGateRepository(session)
        proposals = ProposalApplicationService(repository, clock=lambda: NOW)
        authorizations = AuthorizationApplicationService(
            repository, AllowHumanApproval(), clock=lambda: NOW
        )
        proposal = proposals.create(
            CreateProposalCommand(
                merchant_id="mer_test",
                product_id="prod_test",
                quantity=2,
                idempotency_key="proposal-key",
            ),
            actor(),
        )
        authorizations.request(
            RequestAuthorizationCommand(
                proposal_id=proposal.id,
                idempotency_key="authorization-request-key",
            ),
            actor(),
        )
        authorizations.approve(
            ApproveAuthorizationCommand(
                proposal_id=proposal.id,
                proposal_hash=proposal.proposal_hash,
                max_quantity=proposal.quantity,
                max_amount=proposal.total,
                expires_at=proposal.expires_at,
                idempotency_key="authorization-approve-key",
            ),
            actor(),
        )
        MerchantGateApplicationService(repository, clock=lambda: NOW).evaluate(
            EvaluateMerchantPolicyCommand(proposal_id=proposal.id), actor()
        )
        transaction = TransactionCreationApplicationService(repository, clock=lambda: NOW).create(
            CreateTransactionCommand(
                proposal_id=proposal.id,
                idempotency_key="transaction-create-key",
            ),
            actor(),
        )
        return transaction.id


def service(
    factory: SessionFactory,
    provider: RecordingProvider,
    *,
    clock: Callable[[], datetime] = lambda: NOW,
) -> TransactionExecutionApplicationService:
    return TransactionExecutionApplicationService(
        lambda: SqlAlchemyExecutionUnitOfWork(factory, clock=clock),
        provider,
        provider=ProviderName.RAZORPAY,
        clock=clock,
    )


def test_execute_commits_before_dispatch_and_reuses_one_durable_attempt(tmp_path: Path) -> None:
    with execution_database(tmp_path / "execute.db") as (_, factory):
        transaction_id = seed_ready_transaction(factory)

        def assert_pre_dispatch_commit(command: CreateProviderOrderCommand) -> None:
            with factory() as session:
                transaction = session.get(models.Transaction, command.transaction_id)
                attempt = session.get(models.PaymentAttempt, command.attempt_id)
                idempotency = session.scalar(
                    select(models.IdempotencyRecord).where(
                        models.IdempotencyRecord.resource_id == command.transaction_id
                    )
                )
                assert transaction is not None
                assert transaction.state == TransactionState.EXECUTING.value
                assert attempt is not None
                assert attempt.provider_request_fingerprint == command.request_fingerprint
                assert idempotency is not None
                assert idempotency.response_code is None

        provider = RecordingProvider(before_response=assert_pre_dispatch_commit)
        execution = service(factory, provider)
        command = ExecuteTransactionCommand(
            transaction_id=transaction_id, idempotency_key="execute-key"
        )

        result = execution.execute(command, actor())
        repeated = execution.execute(command, actor())
        other_key = execution.execute(
            ExecuteTransactionCommand(
                transaction_id=transaction_id, idempotency_key="execute-key-2"
            ),
            actor(),
        )

        assert result.state is TransactionState.PAYMENT_PENDING
        assert repeated == result
        assert other_key.state is TransactionState.PAYMENT_PENDING
        assert provider.call_count == 1
        assert result.provider_phase is not None
        assert result.provider_phase.order_state == "created"
        sent = provider.commands[0]
        assert sent.transaction_id == transaction_id
        assert sent.receipt == transaction_id
        assert sent.amount.amount_minor == 100_000
        assert sent.amount.currency == "INR"
        assert sent.attempt_id.startswith("pay_")
        assert sent.request_fingerprint.startswith("sha256:")
        with factory() as session:
            assert session.scalar(select(func.count()).select_from(models.PaymentAttempt)) == 1
            assert session.scalar(select(func.count()).select_from(models.IdempotencyRecord)) == 2
            events = session.scalars(
                select(models.TransactionEvent).where(
                    models.TransactionEvent.transaction_id == transaction_id
                )
            ).all()
            transitions = {
                (event.previous_state, event.new_state, event.reason_code) for event in events
            }
            assert transitions == {
                (None, TransactionState.READY.value, "GATES_SATISFIED"),
                (
                    TransactionState.READY.value,
                    TransactionState.EXECUTING.value,
                    "PROVIDER_ATTEMPT_CREATED",
                ),
                (
                    TransactionState.EXECUTING.value,
                    TransactionState.PAYMENT_PENDING.value,
                    "PROVIDER_ORDER_CREATED",
                ),
            }
            provider_event = next(
                event
                for event in events
                if event.new_state == TransactionState.PAYMENT_PENDING.value
            )
            assert provider_event.provider_reference_redacted == "...1234"
            assert "order_test_1234" not in str(provider_event.metadata_json)
            assert provider_event.metadata_json["buyer_id"] == "buy_test"
            assert provider_event.metadata_json["merchant_id"] == "mer_test"


def test_same_idempotency_key_rejects_a_different_fingerprint(tmp_path: Path) -> None:
    with execution_database(tmp_path / "fingerprint.db") as (_, factory):
        transaction_id = seed_ready_transaction(factory)
        provider = RecordingProvider()
        execution = service(factory, provider)
        execution.execute(
            ExecuteTransactionCommand(transaction_id=transaction_id, idempotency_key="shared-key"),
            actor(),
        )

        with pytest.raises(AppError) as error:
            execution.execute(
                ExecuteTransactionCommand(
                    transaction_id="txn_another_request", idempotency_key="shared-key"
                ),
                actor(),
            )
        assert error.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSED
        assert provider.call_count == 1


@pytest.mark.parametrize(
    ("drift", "expected_code"),
    [
        ("product", ErrorCode.PROPOSAL_STALE),
        ("authorization", ErrorCode.AUTHORIZATION_INVALID),
        ("policy", ErrorCode.MERCHANT_REVIEW_REQUIRED),
    ],
)
def test_execution_revalidates_every_gate_before_attempt(
    tmp_path: Path, drift: str, expected_code: ErrorCode
) -> None:
    with execution_database(tmp_path / "revalidate.db") as (_, factory):
        transaction_id = seed_ready_transaction(factory)
        with factory.begin() as session:
            if drift == "product":
                product = session.get(models.Product, "prod_test")
                assert product is not None
                product.version += 1
            elif drift == "authorization":
                transaction = session.get(models.Transaction, transaction_id)
                assert transaction is not None
                authorization = session.get(
                    models.BuyerAuthorization, transaction.buyer_authorization_id
                )
                assert authorization is not None
                authorization.status = AuthorizationStatus.REVOKED.value
            else:
                session.add(
                    models.MerchantPolicy(
                        id="pol_test_v2",
                        merchant_id="mer_test",
                        mode=PolicyMode.DENY_ALL.value,
                        auto_accept_max_minor=None,
                        currency=None,
                        version=2,
                        status="ACTIVE",
                    )
                )
        provider = RecordingProvider()

        with pytest.raises(AppError) as error:
            service(factory, provider).execute(
                ExecuteTransactionCommand(
                    transaction_id=transaction_id, idempotency_key="stale-product"
                ),
                actor(),
            )
        assert error.value.code is expected_code
        assert provider.call_count == 0
        with factory() as session:
            assert session.scalar(select(func.count()).select_from(models.PaymentAttempt)) == 0
            assert session.scalar(select(func.count()).select_from(models.IdempotencyRecord)) == 0


def test_unknown_outcome_is_durable_and_never_blindly_retried(tmp_path: Path) -> None:
    with execution_database(tmp_path / "unknown.db") as (_, factory):
        transaction_id = seed_ready_transaction(factory)
        provider = RecordingProvider(error=TimeoutError("provider timed out"))
        execution = service(factory, provider)
        command = ExecuteTransactionCommand(
            transaction_id=transaction_id, idempotency_key="timeout-key"
        )

        with pytest.raises(AppError) as first_error:
            execution.execute(command, actor())
        assert first_error.value.code is ErrorCode.PROVIDER_OUTCOME_UNKNOWN
        with pytest.raises(AppError) as repeated_error:
            execution.execute(command, actor())
        assert repeated_error.value.code is ErrorCode.PROVIDER_OUTCOME_UNKNOWN

        restarted_provider = RecordingProvider()
        restarted = service(factory, restarted_provider)
        status = restarted.execute(
            ExecuteTransactionCommand(
                transaction_id=transaction_id, idempotency_key="after-restart-key"
            ),
            actor(),
        )
        assert status.state is TransactionState.UNKNOWN
        assert provider.call_count == 1
        assert restarted_provider.call_count == 0
        with factory() as session:
            transaction = session.get(models.Transaction, transaction_id)
            record = session.scalar(
                select(models.IdempotencyRecord).where(
                    models.IdempotencyRecord.idempotency_key == "timeout-key"
                )
            )
            assert transaction is not None
            assert transaction.state == TransactionState.UNKNOWN.value
            assert record is not None
            assert record.response_code == 503
            assert session.scalar(select(func.count()).select_from(models.PaymentAttempt)) == 1


def test_incomplete_provider_observation_is_unknown_not_success(tmp_path: Path) -> None:
    with execution_database(tmp_path / "incomplete.db") as (_, factory):
        transaction_id = seed_ready_transaction(factory)
        provider = IncompleteObservationProvider()

        with pytest.raises(AppError) as error:
            service(factory, provider).execute(
                ExecuteTransactionCommand(
                    transaction_id=transaction_id,
                    idempotency_key="incomplete-observation-key",
                ),
                actor(),
            )
        assert error.value.code is ErrorCode.PROVIDER_OUTCOME_UNKNOWN
        assert provider.call_count == 1
        with factory() as session:
            transaction = session.get(models.Transaction, transaction_id)
            assert transaction is not None
            assert transaction.state == TransactionState.UNKNOWN.value
            assert transaction.state != TransactionState.SUCCEEDED.value


def test_process_crash_after_dispatch_commit_does_not_create_another_attempt(
    tmp_path: Path,
) -> None:
    with execution_database(tmp_path / "crash.db") as (_, factory):
        transaction_id = seed_ready_transaction(factory)
        crashing_provider = CrashingProvider()
        command = ExecuteTransactionCommand(
            transaction_id=transaction_id, idempotency_key="crash-key"
        )

        with pytest.raises(KeyboardInterrupt):
            service(factory, crashing_provider).execute(command, actor())

        restarted_provider = RecordingProvider()
        result = service(factory, restarted_provider).execute(command, actor())
        assert result.state is TransactionState.EXECUTING
        assert crashing_provider.call_count == 1
        assert restarted_provider.call_count == 0
        with factory() as session:
            assert session.scalar(select(func.count()).select_from(models.PaymentAttempt)) == 1


def test_overlapping_calls_observe_executing_and_only_one_dispatches(tmp_path: Path) -> None:
    with execution_database(tmp_path / "concurrent.db") as (_, factory):
        transaction_id = seed_ready_transaction(factory)
        provider_entered = Event()
        allow_provider_response = Event()

        def block_provider(_: CreateProviderOrderCommand) -> None:
            provider_entered.set()
            assert allow_provider_response.wait(timeout=5)

        provider = RecordingProvider(before_response=block_provider)
        execution = service(factory, provider)
        first_command = ExecuteTransactionCommand(
            transaction_id=transaction_id, idempotency_key="concurrent-key"
        )

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(execution.execute, first_command, actor())
            assert provider_entered.wait(timeout=5)
            second = pool.submit(
                execution.execute,
                ExecuteTransactionCommand(
                    transaction_id=transaction_id,
                    idempotency_key="concurrent-independent-key",
                ),
                actor(),
            )
            overlapping_result = second.result(timeout=5)
            assert overlapping_result.state is TransactionState.EXECUTING
            assert provider.call_count == 1
            allow_provider_response.set()
            final_result = first.result(timeout=5)

        assert final_result.state is TransactionState.PAYMENT_PENDING
        assert provider.call_count == 1
        with factory() as session:
            assert session.scalar(select(func.count()).select_from(models.PaymentAttempt)) == 1
            assert session.scalar(select(func.count()).select_from(models.IdempotencyRecord)) == 2


def test_simultaneous_same_key_claim_is_database_deduplicated(tmp_path: Path) -> None:
    with execution_database(tmp_path / "claim-contention.db") as (_, factory):
        transaction_id = seed_ready_transaction(factory)
        start = Event()
        provider = RecordingProvider()
        execution = service(factory, provider)
        command = ExecuteTransactionCommand(
            transaction_id=transaction_id, idempotency_key="contended-key"
        )

        def execute_after_start() -> TransactionState:
            assert start.wait(timeout=5)
            return execution.execute(command, actor()).state

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(execute_after_start)
            second = pool.submit(execute_after_start)
            start.set()
            states = {first.result(timeout=10), second.result(timeout=10)}

        assert states <= {TransactionState.EXECUTING, TransactionState.PAYMENT_PENDING}
        assert TransactionState.PAYMENT_PENDING in states
        assert provider.call_count == 1
        with factory() as session:
            assert session.scalar(select(func.count()).select_from(models.IdempotencyRecord)) == 1
            assert session.scalar(select(func.count()).select_from(models.PaymentAttempt)) == 1


def test_cross_buyer_cannot_execute_or_claim_an_idempotency_key(tmp_path: Path) -> None:
    with execution_database(tmp_path / "tenant.db") as (_, factory):
        transaction_id = seed_ready_transaction(factory)
        provider = RecordingProvider()

        with pytest.raises(AppError) as error:
            service(factory, provider).execute(
                ExecuteTransactionCommand(
                    transaction_id=transaction_id, idempotency_key="foreign-key"
                ),
                actor("buy_other"),
            )
        assert error.value.code is ErrorCode.FORBIDDEN
        assert provider.call_count == 0
        with factory() as session:
            assert session.scalar(select(func.count()).select_from(models.IdempotencyRecord)) == 0
            assert session.scalar(select(func.count()).select_from(models.PaymentAttempt)) == 0


@pytest.mark.integration
def test_postgresql_concurrent_execution_creates_one_attempt_when_configured() -> None:
    database_url = get_settings().test_database_url
    if not database_url:
        pytest.skip("database.test_url is not configured")
    if "postgresql" not in database_url:
        pass

    schema = f"b3_execution_{uuid4().hex}"
    administration_engine = create_engine(database_url, pool_pre_ping=True)
    engine: Engine | None = None
    try:
        with administration_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            execution_options={"schema_translate_map": {None: schema}},
        )
        models.Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine, expire_on_commit=False)
        transaction_id = seed_ready_transaction(factory)
        start = Event()
        provider = RecordingProvider()
        execution = service(factory, provider)

        def execute_after_start(key: str) -> TransactionState:
            assert start.wait(timeout=5)
            return execution.execute(
                ExecuteTransactionCommand(
                    transaction_id=transaction_id,
                    idempotency_key=key,
                ),
                actor(),
            ).state

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(execute_after_start, "postgres-concurrent-1")
            second = pool.submit(execute_after_start, "postgres-concurrent-2")
            start.set()
            states = {first.result(timeout=15), second.result(timeout=15)}

        assert TransactionState.PAYMENT_PENDING in states
        assert provider.call_count == 1
        with factory() as session:
            assert session.scalar(select(func.count()).select_from(models.PaymentAttempt)) == 1
    finally:
        if engine is not None:
            engine.dispose()
        with administration_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        administration_engine.dispose()


def test_real_razorpay_adapter_seam_creates_order_but_never_success(tmp_path: Path) -> None:
    provider_calls = 0

    def razorpay_api(request: httpx.Request) -> httpx.Response:
        nonlocal provider_calls
        provider_calls += 1
        payload = json.loads(request.read())
        return httpx.Response(
            200,
            json={
                "id": "order_adapter_1234",
                "entity": "order",
                "amount": 100_000,
                "amount_paid": 0,
                "amount_due": 100_000,
                "currency": "INR",
                "receipt": payload["receipt"],
                "status": "created",
                "attempts": 0,
            },
        )

    with execution_database(tmp_path / "razorpay-adapter.db") as (_, factory):
        transaction_id = seed_ready_transaction(factory)
        with httpx.Client(transport=httpx.MockTransport(razorpay_api)) as client:
            provider = RazorpayAdapter(
                key_id="rzp_test_integration",
                key_secret="integration-secret",
                client=client,
            )
            result = service(factory, provider).execute(
                ExecuteTransactionCommand(
                    transaction_id=transaction_id,
                    idempotency_key="razorpay-adapter-key",
                ),
                actor(),
            )

        assert result.state is TransactionState.PAYMENT_PENDING
        assert result.state is not TransactionState.SUCCEEDED
        assert provider_calls == 1
        with factory() as session:
            attempt = session.scalar(select(models.PaymentAttempt))
            assert attempt is not None
            assert attempt.provider_order_id == "order_adapter_1234"
            assert attempt.provider_order_state == "created"
            assert attempt.provider_payment_id is None
            assert attempt.provider_payment_state is None
            assert attempt.capture_state is None
