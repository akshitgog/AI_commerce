"""HTTP client for the trusted merchant catalog service (Agent A).

Used exclusively by the merchant MCP adapter (C7). It speaks the merchant
service's reviewed HTTP contract:

    POST /merchants/{merchant_id}/products
    GET  /merchants/{merchant_id}/products[?cursor=]
    GET  /merchants/{merchant_id}/products/{product_id}
    PATCH /merchants/{merchant_id}/products/{product_id}
    POST /merchants/{merchant_id}/products/{product_id}/publish
    POST /merchants/{merchant_id}/products/{product_id}/unpublish

Authentication is the caller's merchant session bearer token, forwarded
verbatim; the merchant service resolves and authorizes it (membership +
ADMIN/EDITOR roles) server-side. Idempotency keys are forwarded in the
mutation bodies per that contract. Publication confirmation tokens are
consumed only by publish/unpublish and are never logged or echoed.
"""

import logging
from typing import Any

import httpx

from ai_commerce_gateway.contracts.models import Money, ProductPage, ProductView
from ai_commerce_gateway.core.errors import AppError, ErrorCode

logger = logging.getLogger(__name__)

_IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"


class MerchantApiError(AppError):
    """The merchant service rejected the call or is unavailable."""


def _product_url(base: str, merchant_id: str, product_id: str | None = None) -> str:
    url = f"{base.rstrip('/')}/merchants/{merchant_id}/products"
    if product_id is not None:
        url += f"/{product_id}"
    return url


class MerchantApiClient:
    """Sync HTTP client over the merchant catalog service."""

    def __init__(self, client: httpx.Client, base_url: str) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")

    def _request(
        self,
        method: str,
        url: str,
        *,
        auth_token: str,
        body: dict[str, Any] | None = None,
    ) -> Any:
        headers = {"Authorization": f"Bearer {auth_token}"}
        try:
            response = self._client.request(method, url, json=body, headers=headers)
        except httpx.HTTPError as exc:
            logger.error("merchant_api_transport_error path=%s detail=%s", url, type(exc).__name__)
            raise MerchantApiError(
                ErrorCode.INTERNAL_ERROR,
                "The merchant catalog service is unavailable.",
                status_code=503,
            ) from exc
        if response.status_code >= 400:
            payload = _safe_json(response)
            error = payload.get("error") if isinstance(payload, dict) else None
            if isinstance(error, dict) and error.get("code"):
                try:
                    code = ErrorCode(str(error["code"]))
                except ValueError:
                    code = ErrorCode.INTERNAL_ERROR
                raise MerchantApiError(
                    code,
                    str(error.get("message", "Merchant service rejected the request.")),
                    status_code=response.status_code,
                    details=error.get("details") or {},
                )
            raise MerchantApiError(
                ErrorCode.INTERNAL_ERROR,
                f"Merchant service returned HTTP {response.status_code}.",
                status_code=502,
            )
        return _safe_json(response)

    # -- reads (any merchant member) ----------------------------------------

    def get_product(self, *, merchant_id: str, product_id: str, auth_token: str) -> ProductView:
        payload = self._request(
            "GET",
            _product_url(self._base_url, merchant_id, product_id),
            auth_token=auth_token,
        )
        return ProductView.model_validate(payload)

    def list_products(
        self, *, merchant_id: str, auth_token: str, cursor: str | None = None
    ) -> ProductPage:
        url = _product_url(self._base_url, merchant_id)
        if cursor is not None:
            url += f"?cursor={cursor}"
        payload = self._request("GET", url, auth_token=auth_token)
        return ProductPage.model_validate(payload)

    # -- mutations (ADMIN/EDITOR; idempotency key required) ------------------

    def create_product_draft(
        self,
        *,
        merchant_id: str,
        auth_token: str,
        idempotency_key: str,
        sku: str,
        title: str,
        description: str,
        price: Money,
        available_quantity: int,
        category: str | None = None,
    ) -> ProductView:
        payload = self._request(
            "POST",
            _product_url(self._base_url, merchant_id),
            auth_token=auth_token,
            body={
                "sku": sku,
                "title": title,
                "description": description,
                "category": category,
                "price": price.model_dump(),
                "available_quantity": available_quantity,
                "idempotency_key": idempotency_key,
            },
        )
        return ProductView.model_validate(payload)

    def update_product(
        self,
        *,
        merchant_id: str,
        product_id: str,
        auth_token: str,
        idempotency_key: str,
        expected_version: int,
        title: str | None = None,
        description: str | None = None,
        category: str | None = None,
        price: Money | None = None,
        available_quantity: int | None = None,
    ) -> ProductView:
        body: dict[str, Any] = {
            "expected_version": expected_version,
            "idempotency_key": idempotency_key,
        }
        if title is not None:
            body["title"] = title
        if description is not None:
            body["description"] = description
        if category is not None:
            body["category"] = category
        if price is not None:
            body["price"] = price.model_dump()
        if available_quantity is not None:
            body["available_quantity"] = available_quantity
        payload = self._request(
            "PATCH",
            _product_url(self._base_url, merchant_id, product_id),
            auth_token=auth_token,
            body=body,
        )
        return ProductView.model_validate(payload)

    def publish_product(
        self,
        *,
        merchant_id: str,
        product_id: str,
        auth_token: str,
        idempotency_key: str,
        expected_version: int,
        confirmation_token: str,
    ) -> ProductView:
        """Publish a draft with a dashboard-issued confirmation token.

        The token is sent to the merchant service (which verifies, binds and
        burns it) and is never logged or echoed back by this adapter.
        """
        payload = self._request(
            "POST",
            f"{_product_url(self._base_url, merchant_id, product_id)}/publish",
            auth_token=auth_token,
            body={
                "expected_version": expected_version,
                "idempotency_key": idempotency_key,
                "confirmation_token": confirmation_token,
            },
        )
        return ProductView.model_validate(payload)

    def unpublish_product(
        self,
        *,
        merchant_id: str,
        product_id: str,
        auth_token: str,
        idempotency_key: str,
        expected_version: int,
        confirmation_token: str,
    ) -> ProductView:
        payload = self._request(
            "POST",
            f"{_product_url(self._base_url, merchant_id, product_id)}/unpublish",
            auth_token=auth_token,
            body={
                "expected_version": expected_version,
                "idempotency_key": idempotency_key,
                "confirmation_token": confirmation_token,
            },
        )
        return ProductView.model_validate(payload)


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError as exc:
        raise MerchantApiError(
            ErrorCode.INTERNAL_ERROR,
            "Merchant service returned an unreadable response.",
            status_code=502,
        ) from exc
