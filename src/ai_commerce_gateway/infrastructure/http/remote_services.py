"""HTTP client adapters that implement the frozen buyer-facing service
protocols against separately deployed trusted merchant/transaction services.

These adapters exist for the ``buyer_services.mode: remote`` deployment where
the buyer application (chat, UI API and buyer MCP) runs in its own process and
reaches the approved application services of the merchant and transaction
lanes over an internal trusted network.

Wire contract (served by the merchant/transaction deployments):

    Catalog (merchant service):
      POST {catalog_base}/internal/buyer/catalog/search
      GET  {catalog_base}/internal/buyer/catalog/products/{product_id}

    Transaction service:
      POST {transaction_base}/internal/buyer/proposals
      GET  {transaction_base}/internal/buyer/proposals/{proposal_id}
      POST {transaction_base}/internal/buyer/authorizations/request
      POST {transaction_base}/internal/buyer/authorizations/approve
      POST {transaction_base}/internal/buyer/transactions
      POST {transaction_base}/internal/buyer/transactions/{id}/execute
      POST {transaction_base}/internal/buyer/transactions/{id}/reconcile
      GET  {transaction_base}/internal/buyer/transactions/{id}
      GET  {transaction_base}/internal/buyer/transactions?merchant_id=&cursor=
      GET  {transaction_base}/internal/buyer/transactions/{id}/audit?cursor=

Trusted-context headers (server-to-server, never accepted from end users):

    X-Actor-ID            authenticated actor identifier
    X-Actor-Type          BUYER | MERCHANT_USER | SYSTEM
    X-Correlation-ID      request correlation
    Idempotency-Key       required for mutations

Bodies are the frozen contract DTOs serialized as JSON. Responses are either
the corresponding view DTO or the canonical error envelope
``{"error": {"code", "message", "details"}}``, which is re-raised locally as
``AppError`` so error semantics survive the process boundary.
"""

import logging
from typing import Any

import httpx

from ai_commerce_gateway.contracts.models import (
    ActorContext,
    ApproveAuthorizationCommand,
    AuditPage,
    BuyerAuthorizationView,
    CatalogSearchQuery,
    CatalogSearchResult,
    CreateProposalCommand,
    CreateTransactionCommand,
    ExecuteTransactionCommand,
    ProductView,
    PurchaseProposalView,
    ReconcileTransactionCommand,
    RequestAuthorizationCommand,
    TransactionPage,
    TransactionView,
)
from ai_commerce_gateway.core.errors import AppError, ErrorCode

logger = logging.getLogger(__name__)

_ACTOR_ID_HEADER = "X-Actor-ID"
_ACTOR_TYPE_HEADER = "X-Actor-Type"
_CORRELATION_ID_HEADER = "X-Correlation-ID"
_IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"


class RemoteServiceTransportError(AppError):
    """A trusted remote service could not be reached or responded unusably."""

    def __init__(self, service: str, detail: str) -> None:
        super().__init__(
            ErrorCode.INTERNAL_ERROR,
            f"Trusted {service} service is unavailable: {detail}",
            status_code=503,
        )


def _actor_headers(actor: ActorContext) -> dict[str, str]:
    return {
        _ACTOR_ID_HEADER: actor.actor_id,
        _ACTOR_TYPE_HEADER: actor.actor_type.value,
        _CORRELATION_ID_HEADER: actor.correlation_id,
    }


def _raise_for_error_response(service: str, response: httpx.Response) -> None:
    payload = _safe_json(service, response)
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict) and error.get("code"):
        try:
            code = ErrorCode(str(error["code"]))
        except ValueError:
            code = ErrorCode.INTERNAL_ERROR
        raise AppError(
            code,
            str(error.get("message", "Remote service rejected the request.")),
            status_code=response.status_code,
            details=error.get("details") or {},
        )
    raise RemoteServiceTransportError(
        service, f"HTTP {response.status_code} without an error envelope."
    )


def _safe_json(service: str, response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError as exc:
        raise RemoteServiceTransportError(
            service, "response was not valid JSON."
        ) from exc


class _RemoteServiceBase:
    def __init__(self, client: httpx.Client, base_url: str) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")

    def _request(
        self,
        *,
        method: str,
        path: str,
        actor: ActorContext,
        body: Any | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        headers = _actor_headers(actor)
        if idempotency_key is not None:
            headers[_IDEMPOTENCY_KEY_HEADER] = idempotency_key
        url = f"{self._base_url}{path}"
        try:
            response = self._client.request(
                method,
                url,
                json=body if body is not None else None,
                headers=headers,
            )
        except httpx.HTTPError as exc:
            logger.error(
                "remote_service_transport_error service=%s path=%s correlation_id=%s detail=%s",
                type(self).__name__,
                path,
                actor.correlation_id,
                exc,
            )
            raise RemoteServiceTransportError(
                type(self).__name__, str(exc)
            ) from exc
        if response.status_code >= 400:
            _raise_for_error_response(type(self).__name__, response)
        return _safe_json(type(self).__name__, response)


class RemoteCatalogService:
    """``CatalogService`` over the trusted merchant service HTTP API."""

    def __init__(self, client: httpx.Client, base_url: str) -> None:
        self._base = _RemoteServiceBase(client, base_url)

    def search(
        self, query: CatalogSearchQuery, actor: ActorContext
    ) -> CatalogSearchResult:
        payload = self._base._request(
            method="POST",
            path="/internal/buyer/catalog/search",
            actor=actor,
            body=query.model_dump(),
        )
        return CatalogSearchResult.model_validate(payload)

    def get_product(self, product_id: str, actor: ActorContext) -> ProductView:
        payload = self._base._request(
            method="GET",
            path=f"/internal/buyer/catalog/products/{product_id}",
            actor=actor,
        )
        return ProductView.model_validate(payload)


class RemoteProposalService:
    """``ProposalService`` over the trusted transaction service HTTP API."""

    def __init__(self, client: httpx.Client, base_url: str) -> None:
        self._base = _RemoteServiceBase(client, base_url)

    def create(
        self, command: CreateProposalCommand, actor: ActorContext
    ) -> PurchaseProposalView:
        payload = self._base._request(
            method="POST",
            path="/internal/buyer/proposals",
            actor=actor,
            body=command.model_dump(exclude={"idempotency_key"}),
            idempotency_key=command.idempotency_key,
        )
        return PurchaseProposalView.model_validate(payload)

    def get(self, proposal_id: str, actor: ActorContext) -> PurchaseProposalView:
        payload = self._base._request(
            method="GET",
            path=f"/internal/buyer/proposals/{proposal_id}",
            actor=actor,
        )
        return PurchaseProposalView.model_validate(payload)


class RemoteAuthorizationService:
    """``AuthorizationService`` over the trusted transaction service HTTP API.

    ``approve`` exists because the frozen protocol requires it; the buyer
    adapter never exposes it to the AI and the HTTP surface is reached only by
    the human buyer approval endpoint.
    """

    def __init__(self, client: httpx.Client, base_url: str) -> None:
        self._base = _RemoteServiceBase(client, base_url)

    def request(
        self, command: RequestAuthorizationCommand, actor: ActorContext
    ) -> BuyerAuthorizationView:
        payload = self._base._request(
            method="POST",
            path="/internal/buyer/authorizations/request",
            actor=actor,
            body=command.model_dump(exclude={"idempotency_key"}),
            idempotency_key=command.idempotency_key,
        )
        return BuyerAuthorizationView.model_validate(payload)

    def approve(
        self, command: ApproveAuthorizationCommand, actor: ActorContext
    ) -> BuyerAuthorizationView:
        payload = self._base._request(
            method="POST",
            path="/internal/buyer/authorizations/approve",
            actor=actor,
            body=command.model_dump(exclude={"idempotency_key"}),
            idempotency_key=command.idempotency_key,
        )
        return BuyerAuthorizationView.model_validate(payload)


class RemoteTransactionService:
    """``TransactionService`` over the trusted transaction service HTTP API."""

    def __init__(self, client: httpx.Client, base_url: str) -> None:
        self._base = _RemoteServiceBase(client, base_url)

    def create(
        self, command: CreateTransactionCommand, actor: ActorContext
    ) -> TransactionView:
        payload = self._base._request(
            method="POST",
            path="/internal/buyer/transactions",
            actor=actor,
            body=command.model_dump(exclude={"idempotency_key"}),
            idempotency_key=command.idempotency_key,
        )
        return TransactionView.model_validate(payload)

    def execute(
        self, command: ExecuteTransactionCommand, actor: ActorContext
    ) -> TransactionView:
        payload = self._base._request(
            method="POST",
            path=f"/internal/buyer/transactions/{command.transaction_id}/execute",
            actor=actor,
            body={},
            idempotency_key=command.idempotency_key,
        )
        return TransactionView.model_validate(payload)

    def get_status(self, transaction_id: str, actor: ActorContext) -> TransactionView:
        payload = self._base._request(
            method="GET",
            path=f"/internal/buyer/transactions/{transaction_id}",
            actor=actor,
        )
        return TransactionView.model_validate(payload)

    def list_for_merchant(
        self, merchant_id: str, actor: ActorContext, cursor: str | None = None
    ) -> TransactionPage:
        query = f"merchant_id={merchant_id}"
        if cursor is not None:
            query += f"&cursor={cursor}"
        payload = self._base._request(
            method="GET",
            path=f"/internal/buyer/transactions?{query}",
            actor=actor,
        )
        return TransactionPage.model_validate(payload)

    def reconcile(
        self, command: ReconcileTransactionCommand, actor: ActorContext
    ) -> TransactionView:
        payload = self._base._request(
            method="POST",
            path=f"/internal/buyer/transactions/{command.transaction_id}/reconcile",
            actor=actor,
            body={},
            idempotency_key=command.idempotency_key,
        )
        return TransactionView.model_validate(payload)

    def get_audit(
        self, transaction_id: str, actor: ActorContext, cursor: str | None = None
    ) -> AuditPage:
        path = f"/internal/buyer/transactions/{transaction_id}/audit"
        if cursor is not None:
            path += f"?cursor={cursor}"
        payload = self._base._request(method="GET", path=path, actor=actor)
        return AuditPage.model_validate(payload)
