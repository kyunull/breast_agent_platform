import json

from app.profiles.models import ModelProfile
from app.runtime.model_gateway import ChatCompletionResult
from app.runtime.models import PromptOptimization
from app.workflows.models import WorkflowVersion


class FakeOptimizerModel:
    def __init__(self):
        self.calls = []

    def complete(self, profile, messages, response_format=None):
        self.calls.append((profile, messages, response_format))
        if len(self.calls) == 1:
            return ChatCompletionResult(
                content=json.dumps({"answer": "HER2 阳性，建议 MDT 讨论"}, ensure_ascii=False),
                model="fake",
                usage={},
                finish_reason="stop",
                response_id="run-1",
            )
        return ChatCompletionResult(
            content=json.dumps(
                {
                    "candidate_prompt": "请按证据等级输出 HER2 阳性晚期乳腺癌的分层建议，并列出引用。",
                    "result_diff": {"changed": ["evidence_requirement"]},
                },
                ensure_ascii=False,
            ),
            model="fake",
            usage={},
            finish_reason="stop",
            response_id="opt-1",
        )


def _create_and_publish(client, token, graph):
    headers = {"Authorization": f"Bearer {token}"}
    workflow_id = client.post(
        "/api/v1/workflows", headers=headers, json={"name": "Prompt optimization"}
    ).json()["id"]
    patched = client.patch(
        f"/api/v1/workflows/{workflow_id}/draft",
        headers=headers,
        json={"graph": graph, "extraction": {"groups": []}},
    )
    assert patched.status_code == 200, patched.text
    published = client.post(f"/api/v1/workflows/{workflow_id}/publish", headers=headers)
    assert published.status_code == 201, published.text
    return workflow_id, published.json()["version_number"]


def _graph(profile_id):
    return {
        "nodes": [
            {"id": "input", "type": "input", "name": "输入", "output_ports": ["out"]},
            {
                "id": "llm",
                "type": "llm",
                "name": "综合",
                "input_ports": ["in"],
                "output_ports": ["out"],
                "config": {
                    "prompt": "请分析 {{ input }}",
                    "model_profile_ref": profile_id,
                    "citation_required": False,
                },
            },
            {"id": "output", "type": "output", "name": "输出", "input_ports": ["in"]},
        ],
        "edges": [
            {"id": "e1", "source": "input", "target": "llm", "source_port": "out", "target_port": "in"},
            {"id": "e2", "source": "llm", "target": "output", "source_port": "out", "target_port": "in"},
        ],
    }


def test_prompt_optimization_generates_candidate_and_applies_to_new_draft(client, medical_token):
    db = client.app.state.db_factory()
    try:
        profile = ModelProfile(
            name="Optimization model",
            technical_config_json={"provider": "openai_compatible"},
            medical_options_json={"output_style": "structured"},
            exposed_to_medical=True,
            is_active=True,
        )
        db.add(profile)
        db.commit()
        profile_id = profile.id
    finally:
        db.close()

    model = FakeOptimizerModel()
    client.app.state.runtime_provider_factory = lambda **_: {
        "model": model,
        "model_profile": profile,
    }
    workflow_id, version = _create_and_publish(client, medical_token, _graph(profile_id))
    headers = {"Authorization": f"Bearer {medical_token}"}
    run = client.post(
        "/api/v1/runs",
        headers=headers,
        json={
            "workflow_id": workflow_id,
            "version_number": version,
            "input": {"input": "患者资料"},
        },
    )
    assert run.status_code == 201, run.text
    run_id = run.json()["id"]

    created = client.post(
        "/api/v1/prompt-optimizations",
        headers=headers,
        json={
            "run_id": run_id,
            "node_id": "llm",
            "instruction": "增加证据等级和引用要求",
        },
    )
    assert created.status_code == 201, created.text
    candidate = created.json()
    assert candidate["original_prompt"] == "请分析 {{ input }}"
    assert "证据等级" in candidate["candidate_prompt"]
    assert candidate["result_diff"]["changed"] == ["evidence_requirement"]
    assert candidate["status"] == "candidate"
    optimization_request = json.loads(model.calls[1][1][-1]["content"])
    assert "HER2 阳性" in optimization_request["node_output_summary"]["answer"]

    loaded = client.get(f"/api/v1/prompt-optimizations/{candidate['id']}", headers=headers)
    assert loaded.status_code == 200
    assert loaded.json()["id"] == candidate["id"]

    applied = client.post(
        f"/api/v1/prompt-optimizations/{candidate['id']}/apply",
        headers=headers,
        json={},
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["status"] == "applied"

    versions = client.get(f"/api/v1/workflows/{workflow_id}/versions", headers=headers)
    assert versions.status_code == 200
    published = next(item for item in versions.json() if item["version_number"] == version)
    assert published["definition"]["graph"]["nodes"][1]["config"]["prompt"] == "请分析 {{ input }}"

    draft = client.get(f"/api/v1/workflows/{workflow_id}/draft", headers=headers)
    assert draft.status_code == 200
    applied_prompt = draft.json()["graph"]["nodes"][1]["config"]["prompt"]
    assert applied_prompt != "请分析 {{ input }}"

    stale = client.post(
        "/api/v1/prompt-optimizations",
        headers=headers,
        json={
            "run_id": run_id,
            "node_id": "llm",
            "instruction": "再次优化，但不能覆盖已修改草稿",
        },
    )
    assert stale.status_code == 201
    conflict = client.post(
        f"/api/v1/prompt-optimizations/{stale.json()['id']}/apply",
        headers=headers,
        json={},
    )
    assert conflict.status_code == 409
    draft_after_conflict = client.get(f"/api/v1/workflows/{workflow_id}/draft", headers=headers)
    assert draft_after_conflict.json()["graph"]["nodes"][1]["config"]["prompt"] == applied_prompt

    db = client.app.state.db_factory()
    try:
        stored = db.get(PromptOptimization, candidate["id"])
        assert stored is not None
        assert stored.status == "applied"
        assert stored.applied_at is not None
        assert db.scalar(
            __import__("sqlalchemy").select(WorkflowVersion).where(
                WorkflowVersion.workflow_id == workflow_id,
                WorkflowVersion.status == "published",
                WorkflowVersion.version_number == version,
            )
        ).definition_json["graph"]["nodes"][1]["config"]["prompt"] == "请分析 {{ input }}"
    finally:
        db.close()


def test_prompt_optimization_requires_a_successful_llm_trace(client, medical_token, minimal_valid_graph):
    workflow_id, version = _create_and_publish(client, medical_token, minimal_valid_graph)
    headers = {"Authorization": f"Bearer {medical_token}"}
    run = client.post(
        "/api/v1/runs",
        headers=headers,
        json={"workflow_id": workflow_id, "version_number": version, "input": {}},
    )
    assert run.status_code == 201
    response = client.post(
        "/api/v1/prompt-optimizations",
        headers=headers,
        json={"run_id": run.json()["id"], "node_id": "missing", "instruction": "优化"},
    )
    assert response.status_code == 422
