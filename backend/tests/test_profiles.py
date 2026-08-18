import pytest

from app.profiles.models import KnowledgeProfile


def _knowledge_payload(name="Breast KB"):
    return {
        "name": name,
        "description": "approved local knowledgebase",
        "technical_config": {
            "provider": "knowledgebase",
            "top_k": 5,
            "bm25": True,
            "score_threshold": 0.3,
            "deduplication": True,
            "timeout": 30,
            "retries": 2,
            "api_key_ref": "KB_API_KEY_REF",
        },
        "medical_options": {"scope": "active_guidelines"},
        "exposed_to_medical": True,
    }


def test_medical_profile_list_hides_rag_technical_parameters(client, admin_token, medical_token):
    created = client.post(
        "/api/v1/knowledge-profiles",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=_knowledge_payload(),
    )
    assert created.status_code == 201

    response = client.get(
        "/api/v1/knowledge-profiles",
        headers={"Authorization": f"Bearer {medical_token}"},
    )
    assert response.status_code == 200
    body = response.json()[0]
    assert body["name"] == "Breast KB"
    assert body["medical_options"] == {"scope": "active_guidelines"}
    assert "technical_config" not in body
    assert "top_k" not in body
    assert "bm25" not in body
    assert "score_threshold" not in body
    assert "deduplication" not in body


def test_admin_profile_read_contains_technical_configuration(client, admin_token):
    client.post(
        "/api/v1/knowledge-profiles",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=_knowledge_payload(),
    )
    response = client.get(
        "/api/v1/knowledge-profiles",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()[0]["technical_config"]["top_k"] == 5


def test_admin_can_register_generic_http_knowledge_provider(client, admin_token):
    payload = _knowledge_payload("Generic KB")
    payload["technical_config"].update(
        {
            "provider": "generic_http",
            "query_field": "q",
            "result_path": "data.matches",
        }
    )
    response = client.post(
        "/api/v1/knowledge-profiles",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=payload,
    )
    assert response.status_code == 201, response.text


def test_medical_user_cannot_patch_profile(client, admin_token, medical_token):
    created = client.post(
        "/api/v1/knowledge-profiles",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=_knowledge_payload(),
    )
    profile_id = created.json()["id"]
    response = client.patch(
        f"/api/v1/knowledge-profiles/{profile_id}",
        headers={"Authorization": f"Bearer {medical_token}"},
        json={"technical_config": {"top_k": 100}},
    )
    assert response.status_code == 403


def test_technical_profile_values_are_validated_and_secret_values_rejected(client, admin_token):
    invalid = _knowledge_payload("Invalid KB")
    invalid["technical_config"]["top_k"] = 0
    assert client.post(
        "/api/v1/knowledge-profiles",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=invalid,
    ).status_code == 422

    secret_value = _knowledge_payload("Secret KB")
    secret_value["technical_config"]["api_key"] = "sk-live-secret"
    assert client.post(
        "/api/v1/knowledge-profiles",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=secret_value,
    ).status_code == 422


@pytest.mark.parametrize(
    "technical_config",
    [
        {"Provider": "unsupported"},
        {"topK": 0},
        {"scoreThreshold": 2},
        {"reTries": -1},
        {"timeOut": 0},
    ],
)
def test_technical_profile_validation_canonicalizes_key_aliases(
    client,
    admin_token,
    technical_config,
):
    payload = _knowledge_payload("Invalid aliased config")
    payload["technical_config"] = technical_config

    response = client.post(
        "/api/v1/knowledge-profiles",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.parametrize("provider", [[], {}])
def test_technical_profile_rejects_non_string_provider(client, admin_token, provider):
    payload = _knowledge_payload("Invalid provider type")
    payload["technical_config"] = {"provider": provider}

    response = client.post(
        "/api/v1/knowledge-profiles",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=payload,
    )

    assert response.status_code == 422


def test_profile_rejects_nested_secret_values(client, admin_token):
    payload = _knowledge_payload("Nested Secret KB")
    payload["technical_config"]["headers"] = {"apiKey": "raw-secret-token"}

    response = client.post(
        "/api/v1/knowledge-profiles",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=payload,
    )

    assert response.status_code == 422


def test_profile_rejects_hidden_parameters_in_medical_options(client, admin_token):
    payload = _knowledge_payload("Unsafe Medical Options")
    payload["medical_options"] = {
        "scope": "active_guidelines",
        "provider": "openai",
        "baseURL": "https://models.example.test/v1",
        "topK": 99,
        "apiKeyRef": "MODEL_API_KEY_REF",
    }

    response = client.post(
        "/api/v1/knowledge-profiles",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=payload,
    )

    assert response.status_code == 422


def test_medical_profile_read_redacts_legacy_hidden_options(
    client,
    seed_users,
    medical_token,
):
    db = client.app.state.db_factory()
    try:
        db.add(
            KnowledgeProfile(
                name="Legacy unsafe profile",
                technical_config_json={},
                medical_options_json={
                    "scope": "guidelines",
                    "top_k": 99,
                    "APIKey": "raw-secret-token",
                    "openAIApiKey": "raw-prefixed-secret",
                    "requestTimeout": 10,
                },
                exposed_to_medical=True,
                is_active=True,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/api/v1/knowledge-profiles",
        headers={"Authorization": f"Bearer {medical_token}"},
    )

    assert response.status_code == 200
    assert response.json()[0]["medical_options"] == {"scope": "guidelines"}


def test_medical_user_sees_only_active_exposed_profiles(client, admin_token, medical_token):
    exposed = _knowledge_payload("Exposed")
    hidden = _knowledge_payload("Hidden")
    hidden["exposed_to_medical"] = False
    inactive = _knowledge_payload("Inactive")
    inactive["is_active"] = False
    for payload in (exposed, hidden, inactive):
        response = client.post(
            "/api/v1/knowledge-profiles",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=payload,
        )
        assert response.status_code == 201

    response = client.get(
        "/api/v1/knowledge-profiles",
        headers={"Authorization": f"Bearer {medical_token}"},
    )
    assert [item["name"] for item in response.json()] == ["Exposed"]
