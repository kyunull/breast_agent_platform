from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_reports_backend_status() -> None:
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "breast-agent-backend",
    }
