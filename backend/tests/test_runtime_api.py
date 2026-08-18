from sqlalchemy import select

from app.profiles.models import KnowledgeProfile, ModelProfile
from app.runtime.knowledge_gateway import EvidenceRecord
from app.runtime.models import WorkflowRun


def _create_and_publish(client, token, graph, extraction=None, name="Runtime API"):
    headers = {"Authorization": f"Bearer {token}"}
    workflow_id = client.post(
        "/api/v1/workflows", headers=headers, json={"name": name}
    ).json()["id"]
    patched = client.patch(
        f"/api/v1/workflows/{workflow_id}/draft",
        headers=headers,
        json={"graph": graph, "extraction": extraction or {"groups": []}},
    )
    assert patched.status_code == 200, patched.text
    published = client.post(f"/api/v1/workflows/{workflow_id}/publish", headers=headers)
    assert published.status_code == 201, published.text
    return workflow_id, published.json()["version_number"]


def test_sync_run_returns_result_and_node_traces(client, medical_token, minimal_valid_graph):
    workflow_id, version = _create_and_publish(
        client, medical_token, minimal_valid_graph, name="Sync runtime"
    )
    headers = {"Authorization": f"Bearer {medical_token}"}
    response = client.post(
        "/api/v1/runs",
        headers=headers,
        json={
            "workflow_id": workflow_id,
            "version_number": version,
            "mode": "sync",
            "input": {"patient": {"age": 52, "record": "must-not-be-stored"}},
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["output"] == {}
    assert "must-not-be-stored" not in str(body)
    traces = client.get(f"/api/v1/runs/{body['id']}/traces", headers=headers)
    assert traces.status_code == 200
    assert [trace["node_id"] for trace in traces.json()] == ["input", "output"]


def test_async_run_returns_id_and_can_be_polled(client, medical_token, minimal_valid_graph):
    workflow_id, version = _create_and_publish(
        client, medical_token, minimal_valid_graph, name="Async runtime"
    )
    headers = {"Authorization": f"Bearer {medical_token}"}
    created = client.post(
        "/api/v1/runs",
        headers=headers,
        json={
            "workflow_id": workflow_id,
            "version_number": version,
            "mode": "async",
            "input": {},
        },
    )
    assert created.status_code == 202
    assert created.json()["status"] == "queued"
    polled = client.get(f"/api/v1/runs/{created.json()['id']}", headers=headers)
    assert polled.status_code == 200
    assert polled.json()["status"] == "succeeded"


def test_user_cannot_read_another_users_run(
    client,
    medical_token,
    other_medical_token,
    minimal_valid_graph,
):
    workflow_id, version = _create_and_publish(
        client, other_medical_token, minimal_valid_graph, name="Foreign runtime"
    )
    created = client.post(
        "/api/v1/runs",
        headers={"Authorization": f"Bearer {other_medical_token}"},
        json={"workflow_id": workflow_id, "version_number": version, "input": {}},
    )
    response = client.get(
        f"/api/v1/runs/{created.json()['id']}",
        headers={"Authorization": f"Bearer {medical_token}"},
    )
    assert response.status_code == 403


class FakeKnowledge:
    def search(self, query, filters):
        return [
            EvidenceRecord(
                evidence_id="ev-open-1",
                raw_chunk_id="chunk-open-1",
                text=f"可打开的指南原文：{query}",
                score=0.9,
                source_title="CSCO 乳腺癌指南",
                guideline_id="csco",
                version_id="2026",
                locator="page 18",
                source_level="primary_guideline",
                open_url="https://guideline.example.test/page/18",
            )
        ]


def _rag_graph(profile_id):
    return {
        "nodes": [
            {"id": "input", "type": "input", "name": "输入", "output_ports": ["out"]},
            {
                "id": "rag",
                "type": "rag",
                "name": "指南检索",
                "input_ports": ["in"],
                "output_ports": ["out"],
                "config": {
                    "query": "HER2 阳性晚期乳腺癌",
                    "knowledge_profile_ref": profile_id,
                },
            },
            {
                "id": "output",
                "type": "output",
                "name": "输出",
                "input_ports": ["in"],
                "config": {"transfer_fields": ["rag.evidence_refs"]},
            },
        ],
        "edges": [
            {"id": "e1", "source": "input", "target": "rag", "source_port": "out", "target_port": "in"},
            {"id": "e2", "source": "rag", "target": "output", "source_port": "out", "target_port": "in"},
        ],
    }


def test_run_evidence_can_be_opened_and_rag_can_be_previewed(client, medical_token):
    db = client.app.state.db_factory()
    try:
        profile = KnowledgeProfile(
            name="Runtime KB",
            technical_config_json={"provider": "knowledgebase", "base_url": "http://unused"},
            medical_options_json={"scope": "guidelines"},
            exposed_to_medical=True,
            is_active=True,
        )
        db.add(profile)
        db.commit()
        profile_id = profile.id
    finally:
        db.close()
    client.app.state.runtime_provider_factory = lambda **_: {"knowledge": FakeKnowledge()}
    workflow_id, version = _create_and_publish(
        client, medical_token, _rag_graph(profile_id), name="Evidence runtime"
    )
    headers = {"Authorization": f"Bearer {medical_token}"}
    run = client.post(
        "/api/v1/runs",
        headers=headers,
        json={"workflow_id": workflow_id, "version_number": version, "input": {}},
    )
    assert run.status_code == 201, run.text
    assert run.json()["output"]["evidence_refs"] == ["ev-open-1"]

    evidence = client.get(
        f"/api/v1/runs/{run.json()['id']}/evidence/ev-open-1",
        headers=headers,
    )
    assert evidence.status_code == 200
    assert evidence.json()["text"].startswith("可打开的指南原文")
    assert evidence.json()["open_url"].endswith("/page/18")

    preview = client.post(
        "/api/v1/knowledge/retrieve/preview",
        headers=headers,
        json={
            "knowledge_profile_id": profile_id,
            "query": "HER2 阳性晚期乳腺癌",
            "guideline_ids": ["csco"],
            "version_ids": ["2026"],
            "language": "zh",
        },
    )
    assert preview.status_code == 200
    assert preview.json()["evidence"][0]["evidence_id"] == "ev-open-1"


def test_failed_run_persists_node_error_trace(client, medical_token):
    graph = {
        "nodes": [
            {"id": "input", "type": "input", "name": "输入", "output_ports": ["out"]},
            {"id": "rule", "type": "python_rule", "name": "失败规则", "input_ports": ["in"], "output_ports": ["out"], "config": {"code": "raise ValueError('patient-secret-张三')"}},
            {"id": "output", "type": "output", "name": "输出", "input_ports": ["in"]},
        ],
        "edges": [
            {"id": "e1", "source": "input", "target": "rule", "source_port": "out", "target_port": "in"},
            {"id": "e2", "source": "rule", "target": "output", "source_port": "out", "target_port": "in"},
        ],
    }
    workflow_id, version = _create_and_publish(
        client, medical_token, graph, name="Failed runtime"
    )
    headers = {"Authorization": f"Bearer {medical_token}"}
    response = client.post(
        "/api/v1/runs",
        headers=headers,
        json={"workflow_id": workflow_id, "version_number": version, "input": {}},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "failed"
    assert "patient-secret" not in response.text
    assert "张三" not in response.text
    traces = client.get(f"/api/v1/runs/{response.json()['id']}/traces", headers=headers)
    assert traces.json()[-1]["node_id"] == "rule"
    assert traces.json()[-1]["status"] == "failed"
    assert "patient-secret" not in traces.text
    assert "张三" not in traces.text


def test_medical_user_cannot_use_hidden_model_profile(
    client,
    medical_token,
    minimal_valid_graph,
):
    db = client.app.state.db_factory()
    try:
        profile = ModelProfile(
            name="Hidden model",
            technical_config_json={"provider": "openai_compatible"},
            medical_options_json={},
            exposed_to_medical=False,
            is_active=True,
        )
        db.add(profile)
        db.commit()
        profile_id = profile.id
    finally:
        db.close()
    workflow_id, version = _create_and_publish(
        client, medical_token, minimal_valid_graph, name="Hidden profile runtime"
    )
    response = client.post(
        "/api/v1/runs",
        headers={"Authorization": f"Bearer {medical_token}"},
        json={
            "workflow_id": workflow_id,
            "version_number": version,
            "model_profile_id": profile_id,
            "input": {},
        },
    )
    assert response.status_code == 403
    db = client.app.state.db_factory()
    try:
        assert db.scalar(select(WorkflowRun)) is None
    finally:
        db.close()


class ProfileEchoModel:
    def complete(self, profile, messages, response_format=None):
        return {"content": '{"profile_id":"' + profile.id + '"}'}


def _multi_model_graph(first_profile_id, second_profile_id):
    return {
        "nodes": [
            {"id": "input", "type": "input", "name": "输入", "output_ports": ["out"]},
            {
                "id": "llm_a",
                "type": "llm",
                "name": "模型 A",
                "input_ports": ["in"],
                "output_ports": ["out"],
                "config": {"prompt": "第一步", "model_profile_ref": first_profile_id},
            },
            {
                "id": "llm_b",
                "type": "llm",
                "name": "模型 B",
                "input_ports": ["in"],
                "output_ports": ["out"],
                "config": {"prompt": "第二步", "model_profile_ref": second_profile_id},
            },
            {
                "id": "output",
                "type": "output",
                "name": "输出",
                "input_ports": ["in"],
                "config": {
                    "transfer_fields": [
                        {"name": "first", "path": "llm_a.profile_id"},
                        {"name": "second", "path": "llm_b.profile_id"},
                    ]
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "input", "target": "llm_a", "source_port": "out", "target_port": "in"},
            {"id": "e2", "source": "llm_a", "target": "llm_b", "source_port": "out", "target_port": "in"},
            {"id": "e3", "source": "llm_b", "target": "output", "source_port": "out", "target_port": "in"},
        ],
    }


def test_runtime_uses_each_node_profile_and_persists_model_override(client, medical_token):
    db = client.app.state.db_factory()
    try:
        profiles = [
            ModelProfile(
                name=f"Runtime model {index}",
                technical_config_json={"provider": "openai_compatible"},
                medical_options_json={},
                exposed_to_medical=True,
                is_active=True,
            )
            for index in (1, 2)
        ]
        db.add_all(profiles)
        db.commit()
        first_id, second_id = profiles[0].id, profiles[1].id
    finally:
        db.close()
    client.app.state.runtime_provider_factory = lambda **_: {"model": ProfileEchoModel()}
    workflow_id, version = _create_and_publish(
        client,
        medical_token,
        _multi_model_graph(first_id, second_id),
        name="Multi-model runtime",
    )
    headers = {"Authorization": f"Bearer {medical_token}"}
    native = client.post(
        "/api/v1/runs",
        headers=headers,
        json={"workflow_id": workflow_id, "version_number": version, "input": {}},
    )
    assert native.status_code == 201, native.text
    assert native.json()["output"] == {"first": first_id, "second": second_id}

    overridden = client.post(
        "/api/v1/runs",
        headers=headers,
        json={
            "workflow_id": workflow_id,
            "version_number": version,
            "model_profile_id": second_id,
            "input": {},
        },
    )
    assert overridden.status_code == 201, overridden.text
    assert overridden.json()["model_profile_id"] == second_id
    assert overridden.json()["output"] == {"first": second_id, "second": second_id}


def test_openapi_documents_async_run_response(client):
    responses = client.get("/openapi.json").json()["paths"]["/api/v1/runs"]["post"]["responses"]
    assert {"201", "202"} <= set(responses)
