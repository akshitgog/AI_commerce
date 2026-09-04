from typing import Annotated, Protocol

from fastapi import APIRouter, Header, Request
from pydantic import BaseModel, ConfigDict
from starlette.concurrency import run_in_threadpool

from ai_commerce_gateway.application.provider_verification import (
    ProviderVerificationApplicationService,
)
from ai_commerce_gateway.contracts.models import (
    HandleWebhookCommand,
    TransactionView,
    VerifyCheckoutCommand,
)
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.domain.provider_verification import WebhookProcessingResult
from ai_commerce_gateway.providers.razorpay import (
    RazorpayAdapterError,
    RazorpayConfigurationError,
    RazorpayRequestError,
    RazorpaySignatureError,
)


class CheckoutVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class ProviderVerificationService(Protocol):
    def verify_checkout(
        self, command: VerifyCheckoutCommand, *, correlation_id: str
    ) -> TransactionView: ...

    def handle_webhook(
        self,
        command: HandleWebhookCommand,
        *,
        provider_event_id: str,
        correlation_id: str,
    ) -> WebhookProcessingResult: ...


def create_provider_callback_router(
    service: ProviderVerificationApplicationService | ProviderVerificationService,
) -> APIRouter:
    router = APIRouter()

    @router.post("/checkout/razorpay/verify", response_model=TransactionView)
    def verify_checkout(payload: CheckoutVerificationRequest, request: Request) -> TransactionView:
        try:
            return service.verify_checkout(
                VerifyCheckoutCommand(
                    transaction_id=payload.transaction_id,
                    provider_order_id=payload.razorpay_order_id,
                    provider_payment_id=payload.razorpay_payment_id,
                    signature=payload.razorpay_signature,
                ),
                correlation_id=request.state.correlation_id,
            )
        except RazorpayAdapterError as exc:
            raise _safe_provider_error(exc) from exc

    @router.post("/webhooks/razorpay", status_code=200)
    async def razorpay_webhook(
        request: Request,
        signature: Annotated[str, Header(alias="X-Razorpay-Signature")],
        event_id: Annotated[str, Header(alias="X-Razorpay-Event-Id")],
    ) -> WebhookProcessingResult:
        raw_body = await request.body()
        try:
            return await run_in_threadpool(
                service.handle_webhook,
                HandleWebhookCommand(
                    raw_body=raw_body,
                    signature=signature,
                ),
                provider_event_id=event_id,
                correlation_id=request.state.correlation_id,
            )
        except RazorpayAdapterError as exc:
            raise _safe_provider_error(exc) from exc

    return router


def _safe_provider_error(exc: RazorpayAdapterError) -> AppError:
    if isinstance(exc, RazorpaySignatureError):
        message, status_code = "Provider signature verification failed.", 400
    elif isinstance(exc, RazorpayRequestError):
        message, status_code = "Provider verification request is invalid.", 400
    elif isinstance(exc, RazorpayConfigurationError):
        message, status_code = "Provider verification is unavailable.", 503
    else:
        message, status_code = "Provider verification could not be completed.", 502
    return AppError(ErrorCode.PROVIDER_ERROR, message, status_code=status_code)
