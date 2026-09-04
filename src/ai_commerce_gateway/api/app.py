import contextlib
from collections.abc import AsyncIterator
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
from ai_commerce_gateway.api.session_auth import BuyerSessionService
from ai_commerce_gateway.core.config import Settings, get_settings
from ai_commerce_gateway.core.errors import AppError, ErrorCode, install_error_handlers
from ai_commerce_gateway.infrastructure.database.session import create_engine


def create_app(
    services_factory: BuyerServicesFactory | None = None,
    *,
    settings: Settings | None = None,
) -> FastAPI:
    """Build the buyer application.

    ``services_factory`` is the composition seam: every request (buyer chat,
    buyer UI API, buyer MCP) obtains the real application services through it.
    When omitted, the default composition is selected from configuration and
    never falls back to stub services — it fails fast with remediation
    guidance when neither the integrated in-process services nor the remote
    trusted service URLs are available.

    Buyer identity comes only from HMAC-signed session tokens verified by the
    middleware below; ``X-Buyer-ID`` and request bodies are never trusted.
    """

    settings = settings or get_settings()
    factory = services_factory or compose_default_buyer_services_factory(settings)
    session_service = BuyerSessionService.from_settings(settings)

    # Create the MCP server and its Streamable HTTP ASGI app.
    # streamable_http_path="/" so the mount path IS the endpoint
    # (avoids /mcp/buyer/mcp doubling). The buyer session service authenticates
    # MCP tool calls with the same signed tokens as the HTTP API.
    buyer_mcp = create_buyer_mcp_server(factory, session_service)
    mcp_asgi_app = buyer_mcp.streamable_http_app(
        streamable_http_path="/",
    )

    # The merchant MCP adapter (C7) is mounted only when the trusted merchant
    # service base URL is configured; it shares no tools with the buyer MCP.
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
        merchant_mcp_asgi_app = merchant_mcp.streamable_http_app(
            streamable_http_path="/",
        )

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # The parent lifespan must enter the MCP session managers
        # because Starlette does not run mounted sub-app lifespans.
        async with buyer_mcp.session_manager.run():
            if merchant_mcp is not None:
                async with merchant_mcp.session_manager.run():
                    yield
            else:
                yield

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    install_error_handlers(app)
    app.include_router(buyer_chat_router, prefix="/v1")

    # The composition seam is shared by the HTTP API and the MCP adapter so
    # both surfaces reach exactly the same application services.
    app.state.buyer_services_factory = factory
    app.state.buyer_session_service = session_service
    app.state.settings = settings

    # Mount MCP Streamable HTTP at /mcp/buyer.
    # The official SDK owns HTTP method/session/protocol behavior.
    app.mount("/mcp/buyer", mcp_asgi_app)

    if merchant_mcp_asgi_app is not None:
        # Merchant MCP (C7): disjoint registry, session-passthrough auth,
        # transport-level idempotency for mutations.
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
    async def correlation_id(request: Request, call_next):  # type: ignore[no-untyped-def]
        request.state.correlation_id = (
            request.headers.get("X-Correlation-ID") or f"corr_{uuid4().hex}"
        )
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = request.state.correlation_id
        return response

    @app.middleware("http")
    async def buyer_session_auth(request: Request, call_next):  # type: ignore[no-untyped-def]
        """Resolve the buyer session token to a server-trusted ActorContext.

        Identity comes only from the verified session token. Without a
        configured session secret the gateway is fail-closed: no actor is
        ever attached and buyer endpoints answer 401.
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
#: resolves this attribute at server start, so the default composition (and
#: its fail-fast guard against missing real services) runs at startup, not at
#: import time. Tests import :func:`create_app` and inject their own seam.
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
