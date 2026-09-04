import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from sqlalchemy import text

from ai_commerce_gateway.api.provider_callbacks import (
    ProviderVerificationService,
    create_provider_callback_router,
)
from ai_commerce_gateway.application.composition import TransactionCompositionRoot
from ai_commerce_gateway.core.config import get_settings
from ai_commerce_gateway.core.errors import AppError, ErrorCode, install_error_handlers
from ai_commerce_gateway.infrastructure.database.session import create_engine

logger = logging.getLogger(__name__)
_CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def create_app(
    provider_verification_service: ProviderVerificationService | None = None,
    composition_root: TransactionCompositionRoot | None = None,
) -> FastAPI:
    settings = get_settings()
    logger.setLevel(settings.log_level.upper())
    if provider_verification_service is not None and composition_root is not None:
        raise ValueError(
            "Inject either provider_verification_service or composition_root, not both."
        )

    owned_composition_root = composition_root
    if (
        owned_composition_root is None
        and provider_verification_service is None
        and settings.razorpay_key_id is not None
        and settings.razorpay_key_secret is not None
    ):
        owned_composition_root = TransactionCompositionRoot.from_settings(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            if owned_composition_root is not None:
                owned_composition_root.close()

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    install_error_handlers(app)
    callback_service = provider_verification_service
    if owned_composition_root is not None:
        callback_service = owned_composition_root.provider_verification
        app.state.transaction_composition_root = owned_composition_root
    if callback_service is not None:
        app.include_router(create_provider_callback_router(callback_service))

    @app.middleware("http")
    async def correlation_id(request: Request, call_next):  # type: ignore[no-untyped-def]
        started_at = perf_counter()
        supplied_correlation_id = request.headers.get("X-Correlation-ID", "")
        request.state.correlation_id = (
            supplied_correlation_id
            if _CORRELATION_ID_PATTERN.fullmatch(supplied_correlation_id)
            else f"corr_{uuid4().hex}"
        )
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            duration_ms = (perf_counter() - started_at) * 1000
            response.headers["X-Correlation-ID"] = request.state.correlation_id
            response.headers["Server-Timing"] = f"app;dur={duration_ms:.3f}"
            return response
        finally:
            duration_ms = (perf_counter() - started_at) * 1000
            route = request.scope.get("route")
            route_template = getattr(route, "path", "unmatched")
            logger.info(
                "request_completed method=%s route=%s status=%d duration_ms=%.3f correlation_id=%s",
                request.method,
                route_template,
                status_code,
                duration_ms,
                request.state.correlation_id,
            )

    @app.get("/health/live", tags=["health"])
    def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    def ready() -> dict[str, str]:
        try:
            with create_engine(settings).connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception as exc:
            raise AppError(
                ErrorCode.INTERNAL_ERROR,
                "Database is not ready.",
                status_code=503,
            ) from exc
        return {"status": "ready"}

    return app


app = create_app()
