from dataclasses import dataclass
from typing import cast

import httpx
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from ai_commerce_gateway.application.proposal_gates import (
    TransactionCreationApplicationService,
)
from ai_commerce_gateway.application.provider_verification import (
    ProviderVerificationApplicationService,
)
from ai_commerce_gateway.application.reconciliation import (
    ReconciliationUnitOfWork,
    TransactionReconciliationApplicationService,
)
from ai_commerce_gateway.application.transaction_execution import (
    ExecutionUnitOfWork,
    TransactionExecutionApplicationService,
)
from ai_commerce_gateway.application.transaction_service import (
    TransactionApplicationService,
    TransactionQueryApplicationService,
)
from ai_commerce_gateway.core.config import Settings
from ai_commerce_gateway.domain.enums import ProviderName
from ai_commerce_gateway.infrastructure.database.execution import (
    SqlAlchemyExecutionUnitOfWork,
)
from ai_commerce_gateway.infrastructure.database.proposal_gates import (
    SqlAlchemyProposalGateRepository,
)
from ai_commerce_gateway.infrastructure.database.provider_verification import (
    SqlAlchemyVerificationUnitOfWork,
)
from ai_commerce_gateway.infrastructure.database.session import (
    create_engine,
    create_session_factory,
)
from ai_commerce_gateway.infrastructure.database.transaction_queries import (
    SqlAlchemyTransactionQueryUnitOfWork,
)
from ai_commerce_gateway.providers.razorpay import RazorpayAdapter


@dataclass(frozen=True, slots=True)
class TransactionComposition:
    """Approved B-lane services sharing the same canonical persistence and provider."""

    transactions: TransactionApplicationService
    provider_verification: ProviderVerificationApplicationService


@dataclass(slots=True)
class TransactionCompositionRoot:
    """Process-level owner for the approved database/provider composition."""

    engine: Engine
    session_factory: sessionmaker[Session]
    provider_service: RazorpayAdapter
    provider_verification: ProviderVerificationApplicationService

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        provider_client: httpx.Client | None = None,
    ) -> "TransactionCompositionRoot":
        engine = create_engine(settings)
        session_factory = create_session_factory(engine)
        provider_service = RazorpayAdapter.from_settings(
            settings,
            client=provider_client,
        )
        provider_verification = ProviderVerificationApplicationService(
            lambda: SqlAlchemyVerificationUnitOfWork(session_factory),
            provider_service,
            provider=ProviderName.RAZORPAY,
        )
        return cls(
            engine=engine,
            session_factory=session_factory,
            provider_service=provider_service,
            provider_verification=provider_verification,
        )

    def for_request(self, request_session: Session) -> TransactionComposition:
        return compose_transaction_services(
            request_session=request_session,
            session_factory=self.session_factory,
            provider_service=self.provider_service,
        )

    def close(self) -> None:
        self.provider_service.close()
        self.engine.dispose()


def compose_transaction_services(
    *,
    request_session: Session,
    session_factory: sessionmaker[Session],
    provider_service: RazorpayAdapter,
    provider: ProviderName = ProviderName.RAZORPAY,
) -> TransactionComposition:
    """Compose the one transaction path for an authenticated request boundary.

    ``request_session`` owns transaction creation and must be committed or rolled back by
    the caller's request unit of work. Provider dispatch, reconciliation, verification,
    and reads create their own short-lived database units of work.
    """

    def execution_uow() -> ExecutionUnitOfWork:
        return cast(ExecutionUnitOfWork, SqlAlchemyExecutionUnitOfWork(session_factory))

    def reconciliation_uow() -> ReconciliationUnitOfWork:
        return cast(ReconciliationUnitOfWork, SqlAlchemyExecutionUnitOfWork(session_factory))

    def query_uow() -> SqlAlchemyTransactionQueryUnitOfWork:
        return SqlAlchemyTransactionQueryUnitOfWork(session_factory)

    creation = TransactionCreationApplicationService(
        SqlAlchemyProposalGateRepository(request_session)
    )
    execution = TransactionExecutionApplicationService(
        execution_uow,
        provider_service,
        provider=provider,
    )
    reconciliation = TransactionReconciliationApplicationService(
        reconciliation_uow,
        provider_service,
    )
    queries = TransactionQueryApplicationService(query_uow)
    transactions = TransactionApplicationService(
        creation=creation,
        execution=execution,
        reconciliation=reconciliation,
        queries=queries,
        commit_created_transaction=request_session.commit,
    )
    verification = ProviderVerificationApplicationService(
        lambda: SqlAlchemyVerificationUnitOfWork(session_factory),
        provider_service,
        provider=provider,
    )
    return TransactionComposition(
        transactions=transactions,
        provider_verification=verification,
    )
