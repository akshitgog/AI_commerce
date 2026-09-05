"""Wire-contract tests for the remote buyer service HTTP adapters.

Uses ``httpx.MockTransport`` as an in-test stand-in for the trusted
merchant/transaction service deployments (test fakes are permitted in tests).
Verifies the documented wire contract: paths, methods, trusted-context
headers, idempotency-key forwarding, DTO round-trips and canonical error
envelope mapping.
"""

import json
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from ai_commerce_gateway.contracts.models import ActorContext
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.domain.enums import ActorType
from ai_commerce_gateway.infrastructure.http.remote_services import (
    RemoteCatalogService,
    RemoteServiceTransportError,
)

CATALOG_BASE = "https://catalog.internal"
TRANSACTION_BASE = "https://transactions.internal"


def _actor() -> ActorContext:
    return ActorContext(
        actor_id="buyer_1",
        actor_type=ActorType.BUYER,
        correlation_id="corr_wire_1",
    )


def _client(handler: Any) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_catalog_search_wire_contract() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        seen["actor_id"] = request.headers.get("X-Actor-ID")
        seen["actor_type"] = request.headers.get("X-Actor-Type")
        seen["correlation"] = request.headers.get("X-Correlation-ID")
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "prod_1",
                        "merchant_id": "mer_1",
                        "sku": "SKU-1",
                        "title": "Widget",
                        "description": "d",
                        "category": "c",
                        "price": {"amount_minor": 1000, "currency": "INR"},
                        "available_quantity": 5,
                        "status": "PUBLISHED",
                        "version": 1,
                        "images": [],
                    }
                ],
                "next_cursor": None,
            },
        )

    service = RemoteCatalogService(_client(handler), CATALOG_BASE)
    from ai_commerce_gateway.contracts.models import CatalogSearchQuery

    result = service.search(CatalogSearchQuery(merchant_id="mer_1", query="widget"), _actor())
    assert seen["method"] == "POST"
    assert seen["path"] == "/internal/buyer/catalog/search"
    assert seen["body"]["merchant_id"] == "mer_1"
    assert seen["actor_id"] == "buyer_1"
    assert seen["actor_type"] == "BUYER"
    assert seen["correlation"] == "corr_wire_1"
    assert result.items[0].id == "prod_1"
    assert result.items[0].price.amount_minor == 1000


def test_catalog_get_product_wire_contract() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        return httpx.Response(
            200,
            json={
                "id": "prod_1",
                "merchant_id": "mer_1",
                "sku": "SKU-1",
                "title": "Widget",
                "description": "d",
                "category": "c",
                "price": {"amount_minor": 1000, "currency": "INR"},
                "available_quantity": 5,
                "status": "PUBLISHED",
                "version": 1,
                "images": [],
            },
        )

    service = RemoteCatalogService(_client(handler), CATALOG_BASE)
    product = service.get_product("mer_1", "prod_1", _actor())
    assert seen["method"] == "GET"
    assert seen["path"] == "/internal/buyer/catalog/products/prod_1"
    assert product.id == "prod_1"


def test_transaction_service_wire_contract() -> None:
    from ai_commerce_gateway.contracts.models import (
        CreateTransactionCommand,
        ExecuteTransactionCommand,
    )
    from ai_commerce_gateway.infrastructure.http.remote_services import (
        RemoteTransactionService,
    )

    seen: list[httpx.Request] = []

    transaction_payload = {
        "id": "txn_1",
        "proposal_id": "prop_1",
        "merchant_id": "mer_1",
        "buyer_id": "buyer_1",
        "amount": {"amount_minor": 1000, "currency": "INR"},
        "state": "READY",
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/audit"):
            return httpx.Response(200, json={"items": [], "next_cursor": None})
        return httpx.Response(200, json=transaction_payload)

    service = RemoteTransactionService(_client(handler), TRANSACTION_BASE)
    actor = _actor()

    created = service.create(
        CreateTransactionCommand(proposal_id="prop_1", idempotency_key="idem_c"), actor
    )
    assert created.id == "txn_1"
    assert seen[-1].url.path == "/internal/buyer/transactions"
    assert seen[-1].headers.get("Idempotency-Key") == "idem_c"
    assert "idempotency_key" not in json.loads(seen[-1].content)

    executed = service.execute(
        ExecuteTransactionCommand(transaction_id="txn_1", idempotency_key="idem_e"), actor
    )
    assert executed.id == "txn_1"
    assert seen[-1].url.path == "/internal/buyer/transactions/txn_1/execute"
    assert seen[-1].headers.get("Idempotency-Key") == "idem_e"

    status = service.get_status("txn_1", actor)
    assert status.id == "txn_1"
    assert seen[-1].method == "GET"
    assert seen[-1].url.path == "/internal/buyer/transactions/txn_1"

    audit = service.get_audit("txn_1", actor, cursor="cur_1")
    assert audit.items == ()
    assert seen[-1].url.path == "/internal/buyer/transactions/txn_1/audit"
    assert seen[-1].url.params.get("cursor") == "cur_1"


def test_proposal_and_authorization_wire_contract() -> None:
    from ai_commerce_gateway.contracts.models import (
        CreateProposalCommand,
        RequestAuthorizationCommand,
    )
    from ai_commerce_gateway.infrastructure.http.remote_services import (
        RemoteAuthorizationService,
        RemoteProposalService,
    )

    seen: list[httpx.Request] = []

    proposal_payload = {
        "id": "prop_1",
        "buyer_id": "buyer_1",
        "merchant_id": "mer_1",
        "product_id": "prod_1",
        "product_version": 1,
        "quantity": 1,
        "unit_price": {"amount_minor": 1000, "currency": "INR"},
        "total": {"amount_minor": 1000, "currency": "INR"},
        "proposal_hash": "hash_1",
        "status": "PROPOSED",
        "next_required_gate": "BUYER_AUTH_REQUIRED",
        "expires_at": datetime.now(UTC).isoformat(),
        "created_at": datetime.now(UTC).isoformat(),
    }
    authorization_payload = {
        "id": "auth_1",
        "buyer_id": "buyer_1",
        "proposal_id": "prop_1",
        "proposal_hash": "hash_1",
        "merchant_id": "mer_1",
        "product_id": "prod_1",
        "max_quantity": 1,
        "max_amount": {"amount_minor": 1000, "currency": "INR"},
        "authorized_by": None,
        "status": "REQUESTED",
        "expires_at": datetime.now(UTC).isoformat(),
        "created_at": datetime.now(UTC).isoformat(),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/authorizations/request"):
            return httpx.Response(200, json=authorization_payload)
        return httpx.Response(200, json=proposal_payload)

    client = _client(handler)
    proposals = RemoteProposalService(client, TRANSACTION_BASE)
    authorizations = RemoteAuthorizationService(client, TRANSACTION_BASE)
    actor = _actor()

    proposal = proposals.create(
        CreateProposalCommand(
            merchant_id="mer_1", product_id="prod_1", quantity=1, idempotency_key="idem_p"
        ),
        actor,
    )
    assert proposal.id == "prop_1"
    assert seen[-1].headers.get("Idempotency-Key") == "idem_p"
    assert "idempotency_key" not in json.loads(seen[-1].content)

    fetched = proposals.get("prop_1", actor)
    assert fetched.id == "prop_1"
    assert seen[-1].method == "GET"
    assert seen[-1].url.path == "/internal/buyer/proposals/prop_1"

    authorization = authorizations.request(
        RequestAuthorizationCommand(proposal_id="prop_1", idempotency_key="idem_a"), actor
    )
    assert authorization.id == "auth_1"
    assert authorization.status.value == "REQUESTED"
    assert seen[-1].url.path == "/internal/buyer/authorizations/request"
    assert seen[-1].headers.get("Idempotency-Key") == "idem_a"


def test_error_envelope_maps_to_app_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Product was not found.",
                    "details": {},
                },
                "correlation_id": "corr_wire_1",
            },
        )

    from ai_commerce_gateway.contracts.models import CatalogSearchQuery

    service = RemoteCatalogService(_client(handler), CATALOG_BASE)
    with pytest.raises(AppError) as excinfo:
        service.search(CatalogSearchQuery(merchant_id="mer_1"), _actor())
    assert excinfo.value.code == ErrorCode.NOT_FOUND
    assert excinfo.value.status_code == 404
    assert "not found" in excinfo.value.message.lower()


def test_transport_error_maps_to_503() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    from ai_commerce_gateway.contracts.models import CatalogSearchQuery

    service = RemoteCatalogService(_client(handler), CATALOG_BASE)
    with pytest.raises(RemoteServiceTransportError) as excinfo:
        service.search(CatalogSearchQuery(merchant_id="mer_1"), _actor())
    assert excinfo.value.status_code == 503


def test_unusable_error_response_maps_to_503() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="<html>proxy error</html>")

    from ai_commerce_gateway.contracts.models import CatalogSearchQuery

    service = RemoteCatalogService(_client(handler), CATALOG_BASE)
    with pytest.raises(RemoteServiceTransportError):
        service.search(CatalogSearchQuery(merchant_id="mer_1"), _actor())
