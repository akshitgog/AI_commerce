from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from ai_commerce_gateway.api.buyer_chat.router import router as buyer_chat_router
from ai_commerce_gateway.core.config import get_settings
from ai_commerce_gateway.core.errors import AppError, ErrorCode, install_error_handlers
from ai_commerce_gateway.infrastructure.database.session import create_engine


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    install_error_handlers(app)
    app.include_router(buyer_chat_router, prefix="/v1")

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
