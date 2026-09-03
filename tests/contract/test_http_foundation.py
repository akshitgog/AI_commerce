from fastapi.testclient import TestClient


def test_liveness_and_correlation_contract(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Correlation-ID": "corr_contract"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Correlation-ID"] == "corr_contract"
