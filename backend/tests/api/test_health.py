from fastapi.testclient import TestClient

from app.main import app


def test_live_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"] == {"status": "alive"}
    assert response.headers["x-request-id"]
    assert response.headers["x-trace-id"]
