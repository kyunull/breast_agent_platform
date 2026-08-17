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
    assert len(published.json()["definition_sha256"]) == 64

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


def test_publish_hash_is_stable_for_same_definition(client, medical_token, minimal_valid_graph):
    headers = {"Authorization": f"Bearer {medical_token}"}
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
