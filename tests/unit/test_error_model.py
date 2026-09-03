from fastapi import FastAPI, Query
from fastapi.testclient import TestClient

from ai_commerce_gateway.core.errors import AppError, ErrorCode, install_error_handlers


def test_app_error_uses_stable_envelope_and_correlation_id() -> None:
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise AppError(
            ErrorCode.AUTHORIZATION_REQUIRED,
            "Buyer authorization is required.",
            status_code=403,
        )

    @app.middleware("http")
    async def correlation(request, call_next):  # type: ignore[no-untyped-def]
        request.state.correlation_id = "corr_test"
        return await call_next(request)

    response = TestClient(app).get("/boom")
    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "AUTHORIZATION_REQUIRED",
            "message": "Buyer authorization is required.",
            "details": {},
        },
        "correlation_id": "corr_test",
    }


def test_request_validation_uses_stable_envelope() -> None:
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/validated")
    def validated(quantity: int = Query(ge=1)) -> dict[str, int]:
        return {"quantity": quantity}

    response = TestClient(app).get("/validated?quantity=0")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"]["errors"][0]["location"] == [
        "query",
        "quantity",
    ]
