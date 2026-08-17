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
