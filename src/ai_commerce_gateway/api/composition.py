"""Buyer application composition root.

This module is the single place where the buyer application (Reference Buyer
Chat, buyer UI API and buyer MCP) obtains the real application services it is
allowed to call. It provides three composition strategies:

* ``static_bundle_factory`` — wrap an already-built
  :class:`BuyerServiceBundle` (tests, or any embedding application).
* ``compose_remote_buyer_services_factory`` — build HTTP-client adapters over
  separately deployed trusted merchant/transaction services
  (``buyer_services.mode: remote``).
* ``compose_in_process_buyer_services_factory`` — compose the approved
  in-process application services owned by the merchant and transaction lanes
  (``buyer_services.mode: in_process``). The required modules exist only in
  the integrated repository; on a single-lane checkout this fails fast with
  explicit remediation instructions instead of silently falling back to any
  stub.

The app factory never builds stub services. Test fakes enter only through the
explicit ``BuyerServicesFactory`` seam in tests.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any

import httpx

from ai_commerce_gateway.contracts.models import ActorContext
from ai_commerce_gateway.contracts.services import (
    AuthorizationService,
    CatalogService,
    ProposalService,
    TransactionService,
)
from ai_commerce_gateway.core.config import Settings, get_settings
from ai_commerce_gateway.core.errors import AppError, ErrorCode


@dataclass(frozen=True, slots=True)
class BuyerServiceBundle:
    """The four buyer-facing application services, composed as one unit."""

    catalog: CatalogService
    proposal: ProposalService
    auth: AuthorizationService
    transaction: TransactionService
    merchant_gates: Any | None = None


#: Callable that opens a request-scoped bundle of the real buyer services.
#: The context manager owns the unit of work (commit/rollback for in-process
#: composition; a no-op boundary for remote adapters).
BuyerServicesFactory = Callable[[], AbstractContextManager[BuyerServiceBundle]]


class SessionBuyerApprovalVerifier:
    """Human buyer approval verifier bound to the server-trusted session.

    Implements the transaction lane's ``HumanBuyerApprovalVerifier`` protocol
    structurally: buyer authorization approval is valid only when the acting
    identity is a BUYER actor authenticated by the gateway session layer and
    is exactly the buyer that owns the proposal. The AI never holds this
    identity; it is derived from the authenticated request only.
    """

    def verify(self, *, actor: ActorContext, buyer_id: str) -> str:
        if actor.actor_type.value != "BUYER":
            raise AppError(
                ErrorCode.FORBIDDEN,
                "Only the human buyer can approve their own authorization.",
                status_code=403,
            )
        if actor.actor_id != buyer_id:
            raise AppError(
                ErrorCode.FORBIDDEN,
                "Buyer authorization approval is restricted to the owning buyer.",
                status_code=403,
            )
        return actor.actor_id


def static_bundle_factory(bundle: BuyerServiceBundle) -> BuyerServicesFactory:
    """Wrap a ready-made bundle (stateless services) as a factory."""

    @contextlib.contextmanager
    def factory() -> Iterator[BuyerServiceBundle]:
        yield bundle

    return factory


def compose_remote_buyer_services_factory(
    settings: Settings | None = None,
) -> BuyerServicesFactory:
    """Compose HTTP-client adapters over deployed trusted services."""

    from ai_commerce_gateway.infrastructure.http.remote_services import (
        RemoteAuthorizationService,
        RemoteCatalogService,
        RemoteProposalService,
        RemoteTransactionService,
    )

    config = settings or get_settings()
    catalog_base = config.buyer_services_catalog_base_url
    transaction_base = config.buyer_services_transaction_base_url
    if not catalog_base or not transaction_base:
        raise RuntimeError(
            "buyer_services.mode is 'remote' but base URLs are not configured. "
            "Set buyer_services.catalog_base_url and "
            "buyer_services.transaction_base_url in config/default.yaml, "
            "config/local.yaml or the APP_CONFIG_FILE overlay."
        )
    client = httpx.Client(timeout=config.buyer_services_timeout_seconds)
    return static_bundle_factory(
        BuyerServiceBundle(
            catalog=RemoteCatalogService(client, catalog_base),
            proposal=RemoteProposalService(client, transaction_base),
            auth=RemoteAuthorizationService(client, transaction_base),
            transaction=RemoteTransactionService(client, transaction_base),
        )
    )


def _import_integrated_services() -> Any:
    """Import the approved in-process services owned by the other lanes.

    These modules exist only in the integrated repository where the merchant
    and transaction lanes are present. The imports are intentionally lazy so
    that single-lane checkouts fail with actionable guidance instead of an
    import-time crash.
    """

    from types import SimpleNamespace

    from ai_commerce_gateway.application.buyer_catalog_service import (
        ApplicationCatalogService,
    )
    from ai_commerce_gateway.application.composition import (
        TransactionCompositionRoot,
    )
    from ai_commerce_gateway.application.proposal_gates import (
        AuthorizationApplicationService,
        MerchantGateApplicationService,
        ProposalApplicationService,
    )
    from ai_commerce_gateway.infrastructure.database.merchant_repositories import (
        SqlAlchemyProductImageRepository,
        SqlAlchemyProductRepository,
    )
    from ai_commerce_gateway.infrastructure.database.proposal_gates import (
        SqlAlchemyProposalGateRepository,
    )

    return SimpleNamespace(
        ApplicationCatalogService=ApplicationCatalogService,
        TransactionCompositionRoot=TransactionCompositionRoot,
        AuthorizationApplicationService=AuthorizationApplicationService,
        MerchantGateApplicationService=MerchantGateApplicationService,
        ProposalApplicationService=ProposalApplicationService,
        SqlAlchemyProductImageRepository=SqlAlchemyProductImageRepository,
        SqlAlchemyProductRepository=SqlAlchemyProductRepository,
        SqlAlchemyProposalGateRepository=SqlAlchemyProposalGateRepository,
    )


def compose_in_process_buyer_services_factory(
    settings: Settings | None = None,
    *,
    transaction_root: Any | None = None,
) -> BuyerServicesFactory:
    """Compose the approved in-process merchant/transaction services.

    Reuses the shared ``TransactionCompositionRoot`` (engine, session factory
    and provider adapter) when the host application provides one; otherwise
    builds its own from settings. Mirrors the sibling lanes' reviewed
    composition:

    * catalog — merchant lane ``ApplicationCatalogService`` over the frozen
      product repositories;
    * proposals / authorizations — transaction lane application services over
      the shared proposal-gate repository (one repository per request unit of
      work);
    * transactions — transaction lane ``TransactionCompositionRoot.for_request``
      with its own execution/reconciliation/query units of work;
    * approvals — ``SessionBuyerApprovalVerifier`` binding approval to the
      server-trusted buyer session.
    """

    try:
        integrated = _import_integrated_services()
    except ImportError as exc:
        raise RuntimeError(
            "In-process buyer services require the integrated repository "
            "(merchant and transaction lanes). This checkout only contains the "
            "buyer lane. Either run from the integrated repository, or configure "
            "buyer_services.mode: remote with the trusted service base URLs. "
            "Stub services are never used as a fallback."
        ) from exc

    from ai_commerce_gateway.infrastructure.database.session import session_scope

    config = settings or get_settings()

    owns_root = False
    root = transaction_root
    if root is None:
        if not config.razorpay_key_id or not config.razorpay_key_secret:
            raise RuntimeError(
                "In-process buyer services require Razorpay Test Mode credentials "
                "(razorpay.key_id / razorpay.key_secret) for the transaction lane "
                "provider adapter."
            )
        root = integrated.TransactionCompositionRoot.from_settings(config)
        owns_root = True

    session_factory = root.session_factory
    approval_verifier = SessionBuyerApprovalVerifier()

    @contextlib.contextmanager
    def factory() -> Iterator[BuyerServiceBundle]:
        with session_scope(session_factory) as request_session:
            gates = integrated.SqlAlchemyProposalGateRepository(request_session)
            transaction_services = root.for_request(request_session)
            yield BuyerServiceBundle(
                catalog=integrated.ApplicationCatalogService(
                    integrated.SqlAlchemyProductRepository(request_session),
                    integrated.SqlAlchemyProductImageRepository(request_session),
                ),
                proposal=integrated.ProposalApplicationService(gates),
                auth=integrated.AuthorizationApplicationService(gates, approval_verifier),
                transaction=transaction_services.transactions,
                merchant_gates=integrated.MerchantGateApplicationService(gates),
            )

    # Let the host close the provider/engine when this factory owns the root.
    factory.transaction_root = root if owns_root else None  # type: ignore[attr-defined]

    return factory


def compose_default_buyer_services_factory(
    settings: Settings | None = None,
    *,
    transaction_root: Any | None = None,
) -> BuyerServicesFactory:
    """Select the composition strategy from configuration. Never uses stubs."""

    config = settings or get_settings()
    if config.buyer_services_mode == "remote":
        return compose_remote_buyer_services_factory(config)
    if config.buyer_services_mode == "in_process":
        return compose_in_process_buyer_services_factory(config, transaction_root=transaction_root)
    raise RuntimeError(
        f"Unknown buyer_services.mode: {config.buyer_services_mode!r}. "
        "Supported modes: in_process, remote."
    )
