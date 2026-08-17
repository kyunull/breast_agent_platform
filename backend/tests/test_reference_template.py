def test_reference_template_contains_required_node_families(client, medical_token):
    response = client.get(
        "/api/v1/templates/her2-advanced",
        headers={"Authorization": f"Bearer {medical_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    types = {node["type"] for node in body["graph"]["nodes"]}
    assert {"input", "condition", "clinical_task", "rag", "llm", "subworkflow", "output"} <= types
    labels = {edge.get("branch_label") for edge in body["graph"]["edges"]}
    assert {"是", "否", "证据不足", "资料不足"} <= labels
    assert body["warning"]


def test_medical_user_can_clone_reference_template(client, medical_token):
    response = client.post(
        "/api/v1/templates/her2-advanced/clone",
        headers={"Authorization": f"Bearer {medical_token}"},
        json={"name": "我的 HER2 流程"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "我的 HER2 流程"

    draft = client.get(
        f"/api/v1/workflows/{response.json()['id']}/draft",
        headers={"Authorization": f"Bearer {medical_token}"},
    )
    assert draft.status_code == 200
    assert any(node["type"] == "rag" for node in draft.json()["graph"]["nodes"])
    assert "review_warning" in draft.json()["metadata"]
