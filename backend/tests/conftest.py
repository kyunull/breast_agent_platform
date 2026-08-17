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
