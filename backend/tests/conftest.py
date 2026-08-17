import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.database import Base
from app.main import create_app
from app.users.models import User
from app.core.security import hash_password


@pytest.fixture
def client(tmp_path) -> TestClient:
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}"))
    Base.metadata.create_all(app.state.engine)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def seed_users(client):
    db = client.app.state.db_factory()
    try:
        db.add_all(
            [
                User(
                    username="admin",
                    display_name="Administrator",
                    password_hash=hash_password("admin-pass"),
                    role="admin_developer",
                ),
                User(
                    username="doctor",
                    display_name="Doctor",
                    password_hash=hash_password("doctor-pass"),
                    role="medical_user",
                ),
            ]
        )
        db.commit()
    finally:
        db.close()


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture
def admin_token(client, seed_users):
    return _login(client, "admin", "admin-pass")


@pytest.fixture
def medical_token(client, seed_users):
    return _login(client, "doctor", "doctor-pass")


@pytest.fixture
def other_medical_token(client, seed_users):
    db = client.app.state.db_factory()
    try:
        db.add(
            User(
                username="other-doctor",
                display_name="Other Doctor",
                password_hash=hash_password("other-pass"),
                role="medical_user",
            )
        )
        db.commit()
    finally:
        db.close()
    return _login(client, "other-doctor", "other-pass")


@pytest.fixture
def minimal_valid_graph():
    return {
        "nodes": [
            {"id": "input", "type": "input", "name": "输入", "input_ports": [], "output_ports": ["out"]},
            {"id": "output", "type": "output", "name": "输出", "input_ports": ["in"], "output_ports": []},
        ],
        "edges": [
            {
                "id": "e1",
                "source": "input",
                "target": "output",
                "source_port": "out",
                "target_port": "in",
                "kind": "normal",
            }
        ],
    }


@pytest.fixture
def workflow_owned_by_other(client, other_medical_token, minimal_valid_graph):
    headers = {"Authorization": f"Bearer {other_medical_token}"}
    created = client.post(
        "/api/v1/workflows",
        headers=headers,
        json={"name": "Other workflow", "description": "fixture"},
    )
    assert created.status_code == 201
    workflow_id = created.json()["id"]
    patched = client.patch(
        f"/api/v1/workflows/{workflow_id}/draft",
        headers=headers,
        json={"graph": minimal_valid_graph},
    )
    assert patched.status_code == 200
    return workflow_id
