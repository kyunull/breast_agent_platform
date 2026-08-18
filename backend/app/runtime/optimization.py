import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.runtime.models import NodeTrace, PromptOptimization, WorkflowRun
from app.runtime.service import summarize_input
from app.workflows.models import Workflow, WorkflowVersion
from app.workflows.schemas import WorkflowDraftPatch
from app.workflows.service import get_draft, update_draft


class PromptOptimizationError(ValueError):
    """A client-correctable prompt optimization error."""


def _llm_node(version: WorkflowVersion, node_id: str) -> dict[str, Any]:
    graph = version.definition_json.get("graph", {})
    nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
    for node in nodes:
        if isinstance(node, dict) and node.get("id") == node_id:
            if node.get("type") != "llm":
                raise PromptOptimizationError("selected node is not an LLM node")
            return node
    raise PromptOptimizationError("LLM node was not found in the run version")


def _prompt_field(config: dict[str, Any]) -> str:
    if "prompt" in config:
        return "prompt"
    if "user_prompt" in config:
        return "user_prompt"
    return "prompt"


def _safe_shape(value: Any, depth: int = 0) -> Any:
    """Preserve output structure while excluding node values from candidate records."""

    if depth >= 4:
        return "[truncated]"
    if isinstance(value, dict):
        return {str(key): _safe_shape(child, depth + 1) for key, child in list(value.items())[:30]}
    if isinstance(value, list):
        return [_safe_shape(item, depth + 1) for item in value[:10]]
    if isinstance(value, str):
        return f"[text:{len(value)} chars]"
    if value is None:
        return None
    if isinstance(value, bool):
        return "[boolean]"
    if isinstance(value, (int, float)):
        return "[number]"
    return f"[{type(value).__name__}]"


def _clean_diff(value: Any) -> dict[str, Any]:
    """Keep only short, user-facing change metadata from a model response."""

    if not isinstance(value, dict):
        return {}
    cleaned: dict[str, Any] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key)
        if key == "changed" and isinstance(raw_value, list):
            cleaned[key] = [str(item)[:160] for item in raw_value[:20] if isinstance(item, (str, int, float))]
        elif key in {"summary", "rationale", "expected_effect"} and isinstance(raw_value, str):
            cleaned[key] = raw_value[:500]
    return cleaned


def _latest_successful_trace(db: Session, run_id: str, node_id: str) -> NodeTrace:
    trace = db.scalar(
        select(NodeTrace)
        .where(
            NodeTrace.run_id == run_id,
            NodeTrace.node_id == node_id,
            NodeTrace.status == "succeeded",
        )
        .order_by(NodeTrace.created_at.desc(), NodeTrace.id.desc())
    )
    if trace is None:
        raise PromptOptimizationError("a successful LLM node trace is required")
    return trace


def _model_content(provider: Any, profile: Any, messages: list[dict[str, str]]) -> str:
    if provider is None:
        raise PromptOptimizationError("model provider is not configured")
    if hasattr(provider, "complete"):
        result = provider.complete(profile, messages, response_format={"type": "json_object"})
    else:
        result = provider(messages, {"type": "json_object"})
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        content = result.get("content", result.get("text"))
    else:
        content = getattr(result, "content", None)
    if not isinstance(content, str):
        raise PromptOptimizationError("model provider returned no optimization text")
    return content


def _candidate_from_content(content: str) -> tuple[str, dict[str, Any]]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        payload = {}
    if isinstance(payload, dict):
        candidate = payload.get("candidate_prompt", payload.get("prompt"))
        raw_diff = payload.get("result_diff", {})
        if isinstance(candidate, str) and candidate.strip():
            diff = _clean_diff(raw_diff)
            diff.setdefault("changed", ["prompt"])
            return candidate.strip(), diff
    if content.strip():
        return content.strip(), {"changed": ["prompt"], "response_format": "text"}
    raise PromptOptimizationError("model returned an empty candidate prompt")


def create_prompt_optimization(
    db: Session,
    run_id: str,
    node_id: str,
    instruction: str,
    actor_id: str,
    *,
    model_provider: Any,
    model_profile: Any | None,
) -> PromptOptimization:
    run = db.get(WorkflowRun, run_id)
    if run is None:
        raise PromptOptimizationError("run not found")
    version = db.get(WorkflowVersion, run.workflow_version_id)
    if version is None:
        raise PromptOptimizationError("workflow version not found")
    node = _llm_node(version, node_id)
    config = node.get("config", {})
    if not isinstance(config, dict):
        raise PromptOptimizationError("LLM node configuration is invalid")
    field = _prompt_field(config)
    original_prompt = config.get(field, "")
    if not isinstance(original_prompt, str) or not original_prompt.strip():
        raise PromptOptimizationError("LLM node has no prompt to optimize")
    trace = _latest_successful_trace(db, run.id, node_id)
    messages = [
        {
            "role": "system",
            "content": (
                "你是医疗决策工作流的提示词优化助手。仅返回 JSON 对象，包含 "
                "candidate_prompt（可直接替换的提示词）和 result_diff（不含患者原文的修改摘要）。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "instruction": instruction,
                    "original_prompt": original_prompt,
                    "node_output_summary": summarize_input(
                        trace.output_json or {}, include_text=True
                    ),
                    "workflow_output_summary": summarize_input(
                        run.output_json or {}, include_text=True
                    ),
                    "constraints": [
                        "不得编造指南或证据",
                        "需要证据时明确要求引用",
                        "不要复述任何患者原文或个人信息",
                    ],
                },
                ensure_ascii=False,
            ),
        },
    ]
    candidate_prompt, result_diff = _candidate_from_content(
        _model_content(model_provider, model_profile, messages)
    )
    optimization = PromptOptimization(
        workflow_id=run.workflow_id,
        node_id=node_id,
        source_run_id=run.id,
        original_prompt=original_prompt,
        candidate_prompt=candidate_prompt,
        instruction=instruction,
        model_profile_id=getattr(model_profile, "id", None),
        test_input_sha256=run.input_sha256,
        result_diff_json=result_diff,
        status="candidate",
        created_by=actor_id,
    )
    db.add(optimization)
    db.flush()
    record_audit(
        db,
        actor_id=actor_id,
        action="prompt_optimization.create",
        entity_type="prompt_optimization",
        entity_id=optimization.id,
        metadata={"workflow_id": run.workflow_id, "node_id": node_id, "run_id": run.id},
    )
    return optimization


def apply_prompt_optimization(
    db: Session,
    candidate_id: str,
    actor_id: str,
) -> tuple[PromptOptimization, WorkflowVersion]:
    optimization = db.get(PromptOptimization, candidate_id)
    if optimization is None:
        raise PromptOptimizationError("prompt optimization not found")
    if optimization.status != "candidate":
        raise PromptOptimizationError("prompt optimization is not pending application")
    workflow = db.get(Workflow, optimization.workflow_id)
    if workflow is None:
        raise PromptOptimizationError("workflow not found")
    draft = get_draft(db, workflow.id, for_update=True)
    if draft is None:
        raise PromptOptimizationError("workflow draft not found")
    definition = deepcopy(draft.definition_json)
    graph = definition.get("graph")
    if not isinstance(graph, dict):
        raise PromptOptimizationError("workflow draft graph is invalid")
    nodes = graph.get("nodes")
    if not isinstance(nodes, list):
        raise PromptOptimizationError("workflow draft nodes are invalid")
    target: dict[str, Any] | None = None
    for node in nodes:
        if isinstance(node, dict) and node.get("id") == optimization.node_id:
            target = node
            break
    if target is None or target.get("type") != "llm":
        raise PromptOptimizationError("LLM node is absent from the current draft")
    config = target.setdefault("config", {})
    if not isinstance(config, dict):
        raise PromptOptimizationError("LLM node configuration is invalid")
    prompt_field = _prompt_field(config)
    if config.get(prompt_field, "") != optimization.original_prompt:
        raise PromptOptimizationError("draft prompt changed since this candidate was created")
    config[prompt_field] = optimization.candidate_prompt
    update_draft(
        db,
        workflow,
        draft,
        WorkflowDraftPatch(graph=graph),
        actor_id,
        allow_technical_parameters=True,
    )
    optimization.status = "applied"
    optimization.applied_at = datetime.now(UTC)
    record_audit(
        db,
        actor_id=actor_id,
        action="prompt_optimization.apply",
        entity_type="prompt_optimization",
        entity_id=optimization.id,
        metadata={"workflow_id": workflow.id, "node_id": optimization.node_id, "draft_id": draft.id},
    )
    db.flush()
    return optimization, draft
