from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_endpoint_reports_backend_status() -> None:
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "breast-agent-backend",
    }


def test_configured_frontend_origin_can_complete_cors_preflight() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            cors_origins="http://localhost:5173,http://127.0.0.1:5173",
        )
    )

    response = TestClient(app).options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
