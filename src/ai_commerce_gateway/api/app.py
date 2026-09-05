"""Integrated application entrypoint.

One process serving:
  * merchant catalog/policy API (merchant lane, /merchants)
  * provider callbacks (transaction lane, /webhooks/...)
  * buyer chat + buyer UI API (buyer lane, /v1/buyer)
  * buyer MCP (/mcp/buyer) and merchant MCP (/mcp/merchant, when configured)

Composition seams:
  * transaction/provider services: TransactionCompositionRoot (B7), created
    from settings when Razorpay Test Mode credentials are configured.
  * buyer-facing services: the buyer composition root (P0-1), which reuses
    the shared transaction root in-process and fails closed with 503 on buyer
    surfaces when it cannot be composed (no silent stubs).
"""

import contextlib
import logging
import re
from collections.abc import AsyncIterator
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from ai_commerce_gateway.api.buyer_chat.router import router as buyer_chat_router
from ai_commerce_gateway.api.composition import (
    BuyerServicesFactory,
    compose_default_buyer_services_factory,
)
from ai_commerce_gateway.api.mcp.buyer_server import create_buyer_mcp_server
from ai_commerce_gateway.api.mcp.merchant_server import create_merchant_mcp_server
from ai_commerce_gateway.api.merchant import merchant_router
from ai_commerce_gateway.api.provider_callbacks import (
    ProviderVerificationService,
    create_provider_callback_router,
)
from ai_commerce_gateway.api.session_auth import BuyerSessionService
from ai_commerce_gateway.application.composition import TransactionCompositionRoot
from ai_commerce_gateway.core.config import Settings, get_settings
from ai_commerce_gateway.core.errors import AppError, ErrorCode, install_error_handlers
from ai_commerce_gateway.infrastructure.database.session import (
    create_engine,
    create_session_factory,
)

logger = logging.getLogger(__name__)
_CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def create_app(
    provider_verification_service: ProviderVerificationService | None = None,
    composition_root: TransactionCompositionRoot | None = None,
    services_factory: BuyerServicesFactory | None = None,
    *,
    settings: Settings | None = None,
) -> FastAPI:
    """Build the integrated gateway application.

    ``services_factory`` is the buyer-side composition seam (tests inject
    fakes through it; production composes the real in-process services over
    the shared transaction root, or remote adapters when configured remote).
    """
    settings = settings or get_settings()
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

    session_service = BuyerSessionService.from_settings(settings)

    # Buyer composition: an explicitly injected factory wins (tests/embedders).
    # Otherwise compose lazily on first use so a missing transaction
    # configuration degrades buyer surfaces to 503 instead of crashing the
    # merchant/provider surfaces at startup.
    buyer_factory_state: dict[str, BuyerServicesFactory | None] = {"factory": services_factory}
    buyer_owned_root: list[object] = []

    def buyer_services_scope():  # type: ignore[no-untyped-def]
        """Open a request-scoped buyer service bundle, composing lazily."""
        factory = buyer_factory_state["factory"]
        if factory is None:
            factory = compose_default_buyer_services_factory(
                settings, transaction_root=owned_composition_root
            )
            buyer_factory_state["factory"] = factory
            owned_root = getattr(factory, "transaction_root", None)
            if owned_root is not None:
                buyer_owned_root.append(owned_root)
        return factory()

    # MCP servers: buyer (session-authenticated) and merchant (C7, when the
    # merchant service base URL is configured).
    buyer_mcp = create_buyer_mcp_server(buyer_services_scope, session_service)
    buyer_mcp_asgi_app = buyer_mcp.streamable_http_app(streamable_http_path="/")

    merchant_mcp = None
    merchant_mcp_asgi_app = None
    if settings.merchant_mcp_api_base_url:
        import httpx

        from ai_commerce_gateway.infrastructure.http.merchant_api_client import (
            MerchantApiClient,
        )

        merchant_api_client = MerchantApiClient(
            httpx.Client(timeout=settings.merchant_mcp_timeout_seconds),
            settings.merchant_mcp_api_base_url,
        )
        merchant_mcp = create_merchant_mcp_server(merchant_api_client)
        merchant_mcp_asgi_app = merchant_mcp.streamable_http_app(streamable_http_path="/")

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # The parent lifespan must enter the MCP session managers because
        # Starlette does not run mounted sub-app lifespans.
        async with buyer_mcp.session_manager.run():
            if merchant_mcp is not None:
                async with merchant_mcp.session_manager.run():
                    yield
            else:
                yield
        if owned_composition_root is not None:
            owned_composition_root.close()
        for root in buyer_owned_root:
            root.close()  # type: ignore[attr-defined]

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    install_error_handlers(app)

    # Merchant lane API (durable session factory for its router deps).
    app.include_router(merchant_router)
    engine = create_engine(settings)
    app.state.session_factory = create_session_factory(engine)

    # Mount static files for serving uploaded images
    from pathlib import Path

    from fastapi.staticfiles import StaticFiles

    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(uploads_dir)), name="media")

    # Transaction lane provider callbacks.
    callback_service = provider_verification_service
    if owned_composition_root is not None:
        callback_service = owned_composition_root.provider_verification
        app.state.transaction_composition_root = owned_composition_root
    if callback_service is not None:
        app.include_router(create_provider_callback_router(callback_service))

    # Buyer lane API.
    app.include_router(buyer_chat_router, prefix="/v1")

    app.state.buyer_services_factory = buyer_services_scope
    app.state.buyer_session_service = session_service
    app.state.settings = settings

    app.mount("/mcp/buyer", buyer_mcp_asgi_app)
    if merchant_mcp_asgi_app is not None:
        app.mount("/mcp/merchant", merchant_mcp_asgi_app)

    @app.exception_handler(ValueError)
    async def handle_value_error(request: Request, exc: ValueError) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": ErrorCode.VALIDATION_ERROR,
                    "message": str(exc),
                    "details": {},
                },
                "correlation_id": correlation_id,
            },
        )

    @app.middleware("http")
    async def buyer_session_auth(request: Request, call_next):  # type: ignore[no-untyped-def]
        """Resolve a buyer session token to a server-trusted ActorContext.

        Only the verified HMAC session token is accepted; X-Buyer-ID, request
        bodies and query parameters can never set identity. Without a
        configured session secret the gateway is fail-closed for buyer
        surfaces (401), while merchant and provider surfaces keep working.
        """
        auth_header = request.headers.get("Authorization")
        if session_service is not None and auth_header:
            scheme, _, token = auth_header.partition(" ")
            if scheme.lower() == "bearer" and token.strip():
                actor = session_service.actor_context(
                    token.strip(),
                    correlation_id=getattr(
                        request.state,
                        "correlation_id",
                        request.headers.get("X-Correlation-ID", "unknown"),
                    ),
                )
                if actor is not None:
                    request.state.actor_context = actor
        return await call_next(request)

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


#: Lazily built ASGI entrypoint. ``uvicorn ai_commerce_gateway.api.app:app``
#: resolves this attribute at server start so composition guards run at
#: startup, not import time.
_APP: FastAPI | None = None


def _get_or_build_app() -> FastAPI:
    global _APP
    if _APP is None:
        _APP = create_app()
    return _APP


def __getattr__(name: str) -> object:
    if name == "app":
        return _get_or_build_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
