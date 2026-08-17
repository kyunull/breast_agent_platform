from datetime import datetime, timezone

from sqlalchemy import select

from app.users.models import AuthSession


def test_medical_user_can_login_and_read_own_role(client, seed_users):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "doctor", "password": "doctor-pass"},
    )
    assert response.status_code == 200
    body = response.json()
    token = body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_at"]

    me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "medical_user"


def test_medical_user_cannot_create_users(client, medical_token):
    response = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {medical_token}"},
        json={
            "username": "other",
            "display_name": "Other",
            "password": "secret-pass",
            "role": "medical_user",
        },
    )
    assert response.status_code == 403


def test_auth_rejects_missing_and_bad_credentials(client, seed_users):
    missing = client.get("/api/v1/me")
    assert missing.status_code == 401

    bad = client.post(
        "/api/v1/auth/login",
        json={"username": "doctor", "password": "wrong"},
    )
    assert bad.status_code == 401


def test_logout_revokes_opaque_session_and_raw_token_is_not_stored(client, medical_token):
    logout = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {medical_token}"},
    )
    assert logout.status_code == 204

    invalidated = client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {medical_token}"},
    )
    assert invalidated.status_code == 401

    db = client.app.state.db_factory()
    try:
        sessions = list(db.scalars(select(AuthSession)))
        assert sessions
        assert all(session.token_hash != medical_token for session in sessions)
        assert all(len(session.token_hash) == 64 for session in sessions)
    finally:
        db.close()


def test_admin_can_create_medical_user(client, admin_token):
    response = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "username": "new-doctor",
            "display_name": "New Doctor",
            "password": "new-pass",
            "role": "medical_user",
        },
    )
    assert response.status_code == 201
    assert response.json()["role"] == "medical_user"
    assert "password" not in response.json()


def test_invalid_role_is_rejected_at_api_boundary(client, admin_token):
    response = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "username": "invalid",
            "display_name": "Invalid",
            "password": "secret-pass",
            "role": "clinician",
        },
    )
    assert response.status_code == 422


def test_login_uses_application_session_ttl(client, seed_users):
    client.app.state.settings.session_ttl_hours = 1
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "doctor", "password": "doctor-pass"},
    )
    assert response.status_code == 200
    expires_at = datetime.fromisoformat(response.json()["expires_at"])
    remaining_seconds = (expires_at - datetime.now(timezone.utc)).total_seconds()
    assert 3590 <= remaining_seconds <= 3610
