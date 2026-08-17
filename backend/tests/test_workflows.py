from copy import deepcopy

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.workflows import router as workflow_router


def test_publish_freezes_definition_and_creates_next_draft(client, medical_token, minimal_valid_graph):
    headers = {"Authorization": f"Bearer {medical_token}"}
    created = client.post(
        "/api/v1/workflows",
        headers=headers,
        json={"name": "HER2 test", "description": "demo"},
    )
    assert created.status_code == 201
    workflow_id = created.json()["id"]
    client.patch(
        f"/api/v1/workflows/{workflow_id}/draft",
        headers=headers,
        json={"graph": minimal_valid_graph},
    )

    published = client.post(f"/api/v1/workflows/{workflow_id}/publish", headers=headers)
    assert published.status_code == 201
    assert published.json()["version_number"] == 1
    assert published.json()["definition_sha256"] is None

    draft = client.get(f"/api/v1/workflows/{workflow_id}/draft", headers=headers)
    assert draft.status_code == 200
    assert draft.json()["status"] == "draft"
    assert draft.json()["version_number"] == 0

    update = client.patch(
        f"/api/v1/workflows/{workflow_id}/versions/1",
        headers=headers,
        json={"description": "mutate"},
    )
    assert update.status_code == 405


def test_medical_user_cannot_edit_another_users_workflow(
    client,
    medical_token,
    other_medical_token,
    workflow_owned_by_other,
):
    response = client.patch(
        f"/api/v1/workflows/{workflow_owned_by_other}/draft",
        headers={"Authorization": f"Bearer {medical_token}"},
        json={"description": "unauthorized"},
    )
    assert response.status_code == 403


def test_invalid_graph_cannot_publish(client, medical_token):
    headers = {"Authorization": f"Bearer {medical_token}"}
    created = client.post("/api/v1/workflows", headers=headers, json={"name": "Invalid"})
    workflow_id = created.json()["id"]
    client.patch(
        f"/api/v1/workflows/{workflow_id}/draft",
        headers=headers,
        json={"graph": {"nodes": [], "edges": []}},
    )
    response = client.post(f"/api/v1/workflows/{workflow_id}/publish", headers=headers)
    assert response.status_code == 422


def test_admin_can_list_and_edit_another_users_workflow(client, admin_token, workflow_owned_by_other):
    headers = {"Authorization": f"Bearer {admin_token}"}
    listed = client.get("/api/v1/workflows", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == workflow_owned_by_other for item in listed.json())

    response = client.patch(
        f"/api/v1/workflows/{workflow_owned_by_other}/draft",
        headers=headers,
        json={"description": "admin update"},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "admin update"


def test_publish_hash_is_stable_for_same_definition(client, admin_token, minimal_valid_graph):
    headers = {"Authorization": f"Bearer {admin_token}"}
    created = client.post("/api/v1/workflows", headers=headers, json={"name": "Stable"})
    workflow_id = created.json()["id"]
    client.patch(
        f"/api/v1/workflows/{workflow_id}/draft",
        headers=headers,
        json={"graph": minimal_valid_graph, "extraction": {"groups": []}},
    )
    first = client.post(f"/api/v1/workflows/{workflow_id}/publish", headers=headers).json()
    client.post(f"/api/v1/workflows/{workflow_id}/publish", headers=headers)
    versions = client.get(f"/api/v1/workflows/{workflow_id}/versions", headers=headers).json()
    assert versions[0]["definition_sha256"] == first["definition_sha256"]


def test_medical_user_cannot_store_hidden_parameters_in_workflow(
    client,
    medical_token,
    minimal_valid_graph,
):
    headers = {"Authorization": f"Bearer {medical_token}"}
    workflow_id = client.post(
        "/api/v1/workflows",
        headers=headers,
        json={"name": "Governed medical workflow"},
    ).json()["id"]
    graph = deepcopy(minimal_valid_graph)
    graph["nodes"][0]["config"] = {
        "provider": "openai",
        "model": "gpt-compatible",
        "baseURL": "https://models.example.test/v1",
        "topK": 5,
        "apiKeyRef": "MODEL_API_KEY_REF",
        "apiKey": "raw-secret-token",
    }

    response = client.patch(
        f"/api/v1/workflows/{workflow_id}/draft",
        headers=headers,
        json={"graph": graph},
    )

    assert response.status_code == 422


def test_medical_user_cannot_nest_acronym_secret_in_allowed_node_config(
    client,
    medical_token,
    minimal_valid_graph,
):
    headers = {"Authorization": f"Bearer {medical_token}"}
    workflow_id = client.post(
        "/api/v1/workflows",
        headers=headers,
        json={"name": "Nested secret workflow"},
    ).json()["id"]
    graph = deepcopy(minimal_valid_graph)
    graph["nodes"][0]["config"] = {
        "inputSchema": {"APIKey": "raw-secret-token"},
    }

    response = client.patch(
        f"/api/v1/workflows/{workflow_id}/draft",
        headers=headers,
        json={"graph": graph},
    )

    assert response.status_code == 422


def test_medical_user_cannot_nest_prefixed_governance_keys_in_allowed_node_config(
    client,
    medical_token,
    minimal_valid_graph,
):
    headers = {"Authorization": f"Bearer {medical_token}"}
    workflow_id = client.post(
        "/api/v1/workflows",
        headers=headers,
        json={"name": "Prefixed governance workflow"},
    ).json()["id"]
    graph = deepcopy(minimal_valid_graph)
    graph["nodes"][0]["config"] = {
        "inputSchema": {
            "openAIApiKey": "raw-secret-token",
            "requestTimeout": 10,
        },
    }

    response = client.patch(
        f"/api/v1/workflows/{workflow_id}/draft",
        headers=headers,
        json={"graph": graph},
    )

    assert response.status_code == 422


def test_medical_user_can_use_clinical_names_ending_in_governed_terms_in_schema(
    client,
    medical_token,
    minimal_valid_graph,
):
    headers = {"Authorization": f"Bearer {medical_token}"}
    workflow_id = client.post(
        "/api/v1/workflows",
        headers=headers,
        json={"name": "Clinical schema names workflow"},
    ).json()["id"]
    graph = deepcopy(minimal_valid_graph)
    input_schema = {
        "careProvider": {"type": "string"},
        "riskModel": {"type": "string"},
        "randomSeed": {"type": "string"},
        "clinicalEndpoint": {"type": "string"},
    }
    graph["nodes"][0]["config"] = {"inputSchema": input_schema}

    response = client.patch(
        f"/api/v1/workflows/{workflow_id}/draft",
        headers=headers,
        json={"graph": graph},
    )

    assert response.status_code == 200
    assert response.json()["graph"]["nodes"][0]["config"]["inputSchema"] == input_schema


def test_admin_can_store_technical_parameters_in_workflow(
    client,
    admin_token,
    minimal_valid_graph,
):
    headers = {"Authorization": f"Bearer {admin_token}"}
    workflow_id = client.post(
        "/api/v1/workflows",
        headers=headers,
        json={"name": "Governed admin workflow"},
    ).json()["id"]
    graph = deepcopy(minimal_valid_graph)
    graph["nodes"][0]["config"] = {"temperature": 0.2, "top_k": 5}

    response = client.patch(
        f"/api/v1/workflows/{workflow_id}/draft",
        headers=headers,
        json={"graph": graph},
    )

    assert response.status_code == 200
    published = client.post(
        f"/api/v1/workflows/{workflow_id}/publish",
        headers=headers,
    )
    assert published.status_code == 201
    assert len(published.json()["definition_sha256"]) == 64


def test_admin_cannot_store_raw_secrets_in_workflow(
    client,
    admin_token,
    minimal_valid_graph,
):
    headers = {"Authorization": f"Bearer {admin_token}"}
    workflow_id = client.post(
        "/api/v1/workflows",
        headers=headers,
        json={"name": "Secret rejection workflow"},
    ).json()["id"]
    graph = deepcopy(minimal_valid_graph)
    graph["nodes"][0]["config"] = {"headers": {"Authorization": "Bearer raw-token"}}

    response = client.patch(
        f"/api/v1/workflows/{workflow_id}/draft",
        headers=headers,
        json={"graph": graph},
    )

    assert response.status_code == 422


def test_medical_user_read_redacts_admin_configured_technical_parameters(
    client,
    admin_token,
    other_medical_token,
    workflow_owned_by_other,
    minimal_valid_graph,
):
    graph = deepcopy(minimal_valid_graph)
    graph["nodes"][0]["config"] = {"temperature": 0.2, "top_k": 5}
    updated = client.patch(
        f"/api/v1/workflows/{workflow_owned_by_other}/draft",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"graph": graph},
    )
    assert updated.status_code == 200

    medical_update = client.patch(
        f"/api/v1/workflows/{workflow_owned_by_other}/draft",
        headers={"Authorization": f"Bearer {other_medical_token}"},
        json={"description": "medical revision"},
    )
    assert medical_update.status_code == 200

    response = client.get(
        f"/api/v1/workflows/{workflow_owned_by_other}/draft",
        headers={"Authorization": f"Bearer {other_medical_token}"},
    )

    assert response.status_code == 200
    assert response.json()["graph"]["nodes"][0]["config"] == {}
    assert response.json()["definition_sha256"] is None


def test_immutable_version_routes_require_workflow_access(
    client,
    medical_token,
    other_medical_token,
    workflow_owned_by_other,
):
    path = f"/api/v1/workflows/{workflow_owned_by_other}/versions/1"

    published = client.post(
        f"/api/v1/workflows/{workflow_owned_by_other}/publish",
        headers={"Authorization": f"Bearer {other_medical_token}"},
    )
    assert published.status_code == 201

    assert client.patch(path, json={}).status_code == 401
    assert client.patch(
        path,
        headers={"Authorization": f"Bearer {medical_token}"},
        json={},
    ).status_code == 403
    assert client.patch(
        path,
        headers={"Authorization": f"Bearer {other_medical_token}"},
        json={},
    ).status_code == 405
    assert client.patch(
        f"/api/v1/workflows/{workflow_owned_by_other}/versions/2",
        headers={"Authorization": f"Bearer {other_medical_token}"},
        json={},
    ).status_code == 404


def test_publish_integrity_race_returns_conflict(
    client,
    medical_token,
    minimal_valid_graph,
    monkeypatch,
):
    headers = {"Authorization": f"Bearer {medical_token}"}
    workflow_id = client.post(
        "/api/v1/workflows",
        headers=headers,
        json={"name": "Concurrent publish"},
    ).json()["id"]
    client.patch(
        f"/api/v1/workflows/{workflow_id}/draft",
        headers=headers,
        json={"graph": minimal_valid_graph},
    )

    def raise_integrity_error(*args, **kwargs):
        raise IntegrityError("concurrent publish", {}, Exception("unique conflict"))

    monkeypatch.setattr(workflow_router, "publish_workflow", raise_integrity_error)
    with TestClient(client.app, raise_server_exceptions=False) as race_client:
        response = race_client.post(
            f"/api/v1/workflows/{workflow_id}/publish",
            headers=headers,
        )

    assert response.status_code == 409
