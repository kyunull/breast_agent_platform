from app.profiles.models import KnowledgeProfile, ModelProfile
from app.runtime.knowledge_gateway import EvidenceRecord
from app.runtime.model_gateway import ChatCompletionResult


class IntegrationKnowledge:
    def search(self, query, filters):
        return [
            EvidenceRecord(
                evidence_id="integration-ev-1",
                raw_chunk_id="chunk-1",
                text="HER2 阳性晚期乳腺癌指南原文",
                score=0.97,
                source_title="乳腺癌指南",
                guideline_id="csco",
                version_id="2026",
                locator="第 18 页",
                source_level="primary_guideline",
                open_url="https://guideline.example.test/18",
            )
        ]


class IntegrationModel:
    def complete(self, profile, messages, response_format=None):
        assert "HER2 阳性晚期乳腺癌指南原文" in messages[-1]["content"]
        return ChatCompletionResult(
            content='{"recommendation":"按指南进入 MDT 评估"}',
            model="integration-model",
            usage={"prompt_tokens": 10, "completion_tokens": 8},
            finish_reason="stop",
            response_id="integration-chat-1",
        )


def test_runtime_api_persists_rag_to_llm_evidence_chain(client, medical_token):
    db = client.app.state.db_factory()
    try:
        model_profile = ModelProfile(
            name="Integration model",
            technical_config_json={"provider": "openai_compatible"},
            medical_options_json={"output_style": "structured"},
            exposed_to_medical=True,
            is_active=True,
        )
        knowledge_profile = KnowledgeProfile(
            name="Integration knowledge",
            technical_config_json={"provider": "knowledgebase", "base_url": "http://unused"},
            medical_options_json={"scope": "guidelines"},
            exposed_to_medical=True,
            is_active=True,
        )
        db.add_all([model_profile, knowledge_profile])
        db.commit()
        model_id, knowledge_id = model_profile.id, knowledge_profile.id
    finally:
        db.close()

    client.app.state.runtime_provider_factory = lambda **_: {
        "model": IntegrationModel(),
        "knowledge": IntegrationKnowledge(),
    }
    graph = {
        "nodes": [
            {"id": "input", "type": "input", "name": "输入", "output_ports": ["out"]},
            {
                "id": "rag",
                "type": "rag",
                "name": "检索",
                "input_ports": ["in"],
                "output_ports": ["out"],
                "config": {"query": "HER2 阳性晚期乳腺癌", "knowledge_profile_ref": knowledge_id},
            },
            {
                "id": "llm",
                "type": "llm",
                "name": "综合",
                "input_ports": ["in"],
                "output_ports": ["out"],
                "config": {
                    "prompt": "请引用 {{rag.context_text}}",
                    "model_profile_ref": model_id,
                    "citation_required": True,
                },
            },
            {
                "id": "output",
                "type": "output",
                "name": "输出",
                "input_ports": ["in"],
                "config": {"transfer_fields": ["llm.recommendation", "llm.evidence_refs"]},
            },
        ],
        "edges": [
            {"id": "e1", "source": "input", "target": "rag", "source_port": "out", "target_port": "in"},
            {"id": "e2", "source": "rag", "target": "llm", "source_port": "out", "target_port": "in"},
            {"id": "e3", "source": "llm", "target": "output", "source_port": "out", "target_port": "in"},
        ],
    }
    headers = {"Authorization": f"Bearer {medical_token}"}
    workflow_id = client.post(
        "/api/v1/workflows", headers=headers, json={"name": "Integration workflow"}
    ).json()["id"]
    assert client.patch(
        f"/api/v1/workflows/{workflow_id}/draft",
        headers=headers,
        json={"graph": graph, "extraction": {"groups": []}},
    ).status_code == 200
    published = client.post(f"/api/v1/workflows/{workflow_id}/publish", headers=headers)
    assert published.status_code == 201, published.text
    run = client.post(
        "/api/v1/runs",
        headers=headers,
        json={"workflow_id": workflow_id, "version_number": 1, "input": {}},
    )
    assert run.status_code == 201, run.text
    run_body = run.json()
    assert run_body["output"] == {
        "recommendation": "按指南进入 MDT 评估",
        "evidence_refs": ["integration-ev-1"],
    }
    traces = client.get(f"/api/v1/runs/{run_body['id']}/traces", headers=headers)
    assert [trace["node_id"] for trace in traces.json()] == ["input", "rag", "llm", "output"]
    assert [trace["sequence"] for trace in traces.json()] == [1, 2, 3, 4]
    llm_trace = next(trace for trace in traces.json() if trace["node_id"] == "llm")
    assert llm_trace["input_summary"]
    assert "HER2 阳性晚期乳腺癌指南原文" not in str(llm_trace["input_summary"])
    evidence = client.get(
        f"/api/v1/runs/{run_body['id']}/evidence/integration-ev-1", headers=headers
    )
    assert evidence.status_code == 200
    assert evidence.json()["open_url"] == "https://guideline.example.test/18"
