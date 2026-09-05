import logging

from fastapi.testclient import TestClient

from ai_commerce_gateway.api.app import create_app
from ai_commerce_gateway.core.config import get_settings


def test_liveness_and_correlation_contract(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Correlation-ID": "corr_contract"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Correlation-ID"] == "corr_contract"


def test_request_timing_is_visible_and_logs_exclude_query_secrets(
    client: TestClient, caplog
) -> None:
    with caplog.at_level(logging.INFO, logger="ai_commerce_gateway.api.app"):
        response = client.get(
            "/health/live?token=must-not-appear",
            headers={"X-Correlation-ID": "corr_timing"},
        )

    assert response.status_code == 200
    assert response.headers["server-timing"].startswith("app;dur=")
    message = next(
        record.getMessage()
        for record in caplog.records
        if "request_completed" in record.getMessage()
    )
    assert "method=GET" in message
    assert "route=/health/live" in message
    assert "status=200" in message
    assert "duration_ms=" in message
    assert "correlation_id=corr_timing" in message
    assert "must-not-appear" not in message


def test_untrusted_correlation_id_is_not_reflected_or_logged(client: TestClient, caplog) -> None:
    unsafe = "secret value that must not be logged"
    with caplog.at_level(logging.INFO, logger="ai_commerce_gateway.api.app"):
        response = client.get("/health/live", headers={"X-Correlation-ID": unsafe})

    assert response.status_code == 200
    assert response.headers["x-correlation-id"].startswith("corr_")
    assert unsafe not in caplog.text


def test_configured_test_mode_builds_the_production_composition(monkeypatch) -> None:
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_auto_composition")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "auto-composition-secret")
    get_settings.cache_clear()
    configured_app = create_app()

    with TestClient(configured_app) as configured_client:
        assert configured_client.get("/health/live").status_code == 200
        assert configured_client.post("/checkout/razorpay/verify", json={}).status_code == 422
        assert configured_client.post("/webhooks/razorpay", content=b"{}").status_code == 422
        assert configured_app.state.transaction_composition_root is not None

    get_settings.cache_clear()


def test_failed_request_logs_safe_status_and_timing(
    client: TestClient, caplog, monkeypatch
) -> None:
    def unavailable_database(*args, **kwargs):
        raise RuntimeError("private database location")

    monkeypatch.setattr("ai_commerce_gateway.api.app.create_engine", unavailable_database)
    with caplog.at_level(logging.INFO, logger="ai_commerce_gateway.api.app"):
        response = client.get("/health/ready", headers={"X-Correlation-ID": "corr_failure"})

    assert response.status_code == 503
    message = next(
        record.getMessage()
        for record in caplog.records
        if "route=/health/ready" in record.getMessage()
    )
    assert "status=503" in message
    assert "duration_ms=" in message
    assert "correlation_id=corr_failure" in message
    assert "postgres" not in message.lower()
