import json
import re
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.runtime.conditions import MISSING, evaluate_condition, resolve_value
from app.runtime.context import ExecutionContext, NodeResult
from app.runtime.knowledge_gateway import EvidenceRecord
from app.runtime.python_runner import RestrictedPythonRunner

_TEMPLATE = re.compile(r"{{\s*([^{}]+?)\s*}}")


def _node_type(node: Any) -> str:
    return str(node.type if hasattr(node, "type") else node.get("type", ""))


def _config(node: Any) -> dict[str, Any]:
    value = node.config if hasattr(node, "config") else node.get("config", {})
    return dict(value or {})


def _render(value: Any, context: ExecutionContext) -> Any:
    if not isinstance(value, str):
        return value

    def replace(match: re.Match[str]) -> str:
        resolved = resolve_value(match.group(1).strip(), context)
        if resolved is MISSING or resolved is None:
            return ""
        return str(resolved)

    return _TEMPLATE.sub(replace, value)


def _node_output(context: ExecutionContext, reference: str) -> Any:
    resolved = resolve_value(reference, context)
    return None if resolved is MISSING else resolved


def _python_inputs(config: Mapping[str, Any], context: ExecutionContext) -> dict[str, Any]:
    configured = config.get("inputs")
    if isinstance(configured, Mapping):
        return {
            str(name): _node_output(context, str(reference))
            for name, reference in configured.items()
        }
    if isinstance(configured, list):
        values: dict[str, Any] = {}
        for item in configured:
            if isinstance(item, str):
                values[item.rsplit(".", 1)[-1]] = _node_output(context, item)
            elif isinstance(item, Mapping):
                reference = str(item.get("path", item.get("input", "")))
                name = str(item.get("name", item.get("label", reference.rsplit(".", 1)[-1])))
                values[name] = _node_output(context, reference)
        return values
    values: dict[str, Any] = {}
    for group in context.extracted.values():
        if isinstance(group, Mapping):
            values.update(group)
    return values


def _knowledge_search(
    provider: Any,
    query: str,
    filters: Mapping[str, Any],
) -> list[EvidenceRecord]:
    if provider is None:
        raise RuntimeError("knowledge provider is not configured")
    result = provider.search(query, filters) if hasattr(provider, "search") else provider(query, filters)
    records: list[EvidenceRecord] = []
    for item in result or []:
        if isinstance(item, EvidenceRecord):
            records.append(item)
        elif isinstance(item, Mapping):
            records.append(EvidenceRecord(**item))
        else:
            raise TypeError("knowledge provider returned an invalid evidence record")
    return records


def _model_complete(
    provider: Any,
    profile: Any,
    messages: list[dict[str, str]],
    schema: Any,
) -> str:
    if provider is None:
        raise RuntimeError("model provider is not configured")
    if hasattr(provider, "complete"):
        result = provider.complete(profile, messages, response_format=schema)
    else:
        result = provider(messages, schema)
    if isinstance(result, str):
        return result
    if isinstance(result, Mapping):
        content = result.get("content", result.get("text"))
    else:
        content = getattr(result, "content", None)
    if not isinstance(content, str):
        raise TypeError("model provider returned no text content")
    return content


def _execute_parallel(
    agents: list[Any],
    context: ExecutionContext,
    providers: Mapping[str, Any],
) -> NodeResult:
    def run_agent(agent: Any) -> tuple[str, NodeResult]:
        agent_id = (
            str(agent.get("id", agent.get("name", "agent")))
            if isinstance(agent, Mapping)
            else str(agent)
        )
        if isinstance(agent, Mapping) and agent.get("type"):
            return agent_id, execute_node(agent, context, providers)
        executor = providers.get("agent_executor")
        if executor is None:
            raise RuntimeError("parallel agent definition requires agent_executor")
        value = executor(agent_id, context)
        result = value if isinstance(value, NodeResult) else NodeResult(
            status="succeeded", output=dict(value)
        )
        return agent_id, result

    with ThreadPoolExecutor(max_workers=max(1, len(agents))) as pool:
        results = dict(pool.map(run_agent, agents))
    merged: dict[str, Any] = {}
    evidence: list[EvidenceRecord] = []
    for agent_id, result in results.items():
        merged[agent_id] = result.output
        evidence.extend(result.evidence)
    return NodeResult(status="succeeded", output=merged, evidence=evidence)


def execute_node(node: Any, context: ExecutionContext, providers: Mapping[str, Any]) -> NodeResult:
    node_type = _node_type(node)
    config = _config(node)
    if node_type == "input":
        return NodeResult(status="succeeded", output=dict(context.extracted), selected_ports=["out"])
    if node_type == "condition":
        condition = evaluate_condition(config, context)
        return NodeResult(
            status="branched",
            output={"value": condition.value, "status": condition.status},
            selected_ports=condition.selected_ports,
        )
    if node_type == "python_rule":
        source = str(config.get("code", config.get("content", "")))
        output = RestrictedPythonRunner(
            max_output_chars=int(config.get("max_output_chars", 100_000))
        ).run(
            source,
            _python_inputs(config, context),
            timeout_seconds=float(config.get("timeout_seconds", 2)),
        )
        return NodeResult(status="succeeded", output=output)
    if node_type == "rag":
        query = _render(config.get("query", config.get("query_template", "")), context)
        records = _knowledge_search(
            providers.get("knowledge"), str(query), config.get("filters", {})
        )
        context_text = "\n\n".join(record.text for record in records)
        return NodeResult(
            status="succeeded" if records else "insufficient",
            output={
                "context_text": context_text,
                "evidence_refs": [record.evidence_id for record in records],
                "status": "sufficient" if records else "insufficient",
            },
            evidence=records,
        )
    if node_type == "llm":
        evidence_refs = list(context.evidence)
        if config.get("citation_required") and not evidence_refs:
            return NodeResult(
                status="insufficient",
                output={"status": "insufficient", "message": "缺少可核验知识库引用"},
            )
        system_prompt = _render(config.get("system_prompt", ""), context)
        user_prompt = _render(config.get("prompt", config.get("user_prompt", "")), context)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": str(system_prompt)})
        messages.append({"role": "user", "content": str(user_prompt)})
        content = _model_complete(
            providers.get("model"),
            providers.get("model_profile"),
            messages,
            config.get("output_schema"),
        )
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {"text": content}
        if not isinstance(parsed, dict):
            parsed = {"text": str(parsed)}
        if evidence_refs:
            parsed.setdefault("evidence_refs", evidence_refs)
        return NodeResult(status="succeeded", output=parsed)
    if node_type == "output":
        fields = config.get("transfer_fields", [])
        if not fields:
            output = (
                dict(next(reversed(context.node_outputs.values())))
                if context.node_outputs
                else {}
            )
        else:
            output = {}
            if isinstance(fields, Mapping):
                fields = [{"name": name, "path": path} for name, path in fields.items()]
            for field in fields:
                if isinstance(field, str):
                    name = field.rsplit(".", 1)[-1]
                    path = field
                else:
                    path = str(field.get("path", field.get("input", "")))
                    name = str(
                        field.get("name", field.get("alias", path.rsplit(".", 1)[-1]))
                    )
                value = _node_output(context, path)
                if value is not None:
                    output[name] = value
        return NodeResult(status="succeeded", output=output)
    if node_type == "parallel_agent":
        agents = config.get("agents", [])
        if not isinstance(agents, list):
            raise RuntimeError("parallel_agent agents must be a list")
        return _execute_parallel(agents, context, providers)
    if node_type in {"clinical_task", "subworkflow", "annotation"}:
        return NodeResult(
            status="succeeded",
            output={"description": config.get("description", ""), "status": "todo"},
        )
    raise RuntimeError(f"unsupported node type: {node_type}")
