import re
from collections.abc import Mapping
from typing import Any

TECHNICAL_PARAMETER_KEYS = {
    "api_version",
    "base_url",
    "bm25",
    "deduplication",
    "deployment",
    "embedding_model",
    "endpoint",
    "frequency_penalty",
    "headers",
    "hybrid_weight",
    "max_tokens",
    "model",
    "model_name",
    "presence_penalty",
    "provider",
    "proxy",
    "query_mode",
    "rerank",
    "rerank_model",
    "reranker",
    "retries",
    "score_threshold",
    "search_mode",
    "seed",
    "temperature",
    "timeout",
    "top_k",
    "top_p",
    "verify_tls",
}

MEDICAL_NODE_CONFIG_KEYS = {
    "annotation": {"description", "text"},
    "clinical_task": {"description", "instructions", "required_fields", "task_type"},
    "condition": {"branches", "description", "expression", "operands", "operator"},
    "input": {"description", "fields", "groups", "input_schema", "source"},
    "llm": {
        "citation_required",
        "description",
        "knowledge_profile_ref",
        "model_profile_ref",
        "output_schema",
        "prompt",
        "prompt_ref",
        "show_evidence_links",
        "system_prompt",
        "user_prompt",
    },
    "output": {"description", "format", "output_schema", "transfer_fields"},
    "parallel_agent": {"agents", "description", "strategy"},
    "python_rule": {"code", "content", "description", "inputs", "output_dict", "output_schema"},
    "rag": {
        "citation_required",
        "description",
        "knowledge_profile_ref",
        "output_key",
        "query",
        "query_template",
    },
    "subworkflow": {"description", "human_review_required", "workflow_ref"},
}

MEDICAL_PROFILE_OPTION_KEYS = {
    "capabilities",
    "citation_required",
    "clinical_scope",
    "description",
    "display_name",
    "guideline_scope",
    "label",
    "language",
    "output_style",
    "scope",
    "supported_tasks",
}

_SECRET_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "client_secret",
    "connection_string",
    "credential",
    "credentials",
    "database_url",
    "passwd",
    "password",
    "secret",
    "token",
}
_SECRET_REF_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*_REF$")
_RAW_SECRET_VALUE_PATTERN = re.compile(
    r"(?i)^(?:bearer\s+\S+|sk-[A-Za-z0-9_-]{8,}|"
    r"(?:postgres(?:ql)?|mysql|mariadb|sqlite)\+?[A-Za-z0-9_-]*://\S+|"
    r"https?://[^/@\s]+:[^/@\s]+@\S+)$"
)
_ACRONYM_BOUNDARY = re.compile(r"(?<=[A-Z])(?=[A-Z][a-z])")
_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_KEY_SEPARATOR = re.compile(r"[^A-Za-z0-9]+")
_COMPACT_KEY_ALIASES = {
    key.replace("_", ""): key
    for key in TECHNICAL_PARAMETER_KEYS | _SECRET_KEYS
}
_COMPACT_KEY_ALIASES.update(
    {
        f"{key.replace('_', '')}ref": f"{key}_ref"
        for key in _SECRET_KEYS
    }
)


def normalize_governance_key(key: Any) -> str:
    separated = _ACRONYM_BOUNDARY.sub("_", str(key))
    separated = _CAMEL_CASE_BOUNDARY.sub("_", separated)
    normalized = _KEY_SEPARATOR.sub("_", separated).strip("_").lower()
    return _COMPACT_KEY_ALIASES.get(normalized.replace("_", ""), normalized)


def _is_secret_reference_key(key: str) -> bool:
    return key.endswith("_ref") and key[:-4] in _SECRET_KEYS


def _looks_like_raw_secret(value: str) -> bool:
    return bool(_RAW_SECRET_VALUE_PATTERN.fullmatch(value.strip()))


def validate_governed_payload(
    value: Any,
    *,
    allow_technical_parameters: bool,
    path: str = "payload",
) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = normalize_governance_key(key)
            child_path = f"{path}.{key}"
            if normalized in _SECRET_KEYS:
                raise ValueError(f"{child_path} must use an environment reference")
            if _is_secret_reference_key(normalized):
                if not allow_technical_parameters:
                    raise ValueError(f"{child_path} is restricted to admin/developer users")
                if not isinstance(child, str) or not _SECRET_REF_PATTERN.fullmatch(child):
                    raise ValueError(f"{child_path} must be an uppercase *_REF name")
                continue
            if not allow_technical_parameters and normalized in TECHNICAL_PARAMETER_KEYS:
                raise ValueError(f"{child_path} is restricted to admin/developer users")
            validate_governed_payload(
                child,
                allow_technical_parameters=allow_technical_parameters,
                path=child_path,
            )
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            validate_governed_payload(
                child,
                allow_technical_parameters=allow_technical_parameters,
                path=f"{path}[{index}]",
            )
        return
    if isinstance(value, str) and _looks_like_raw_secret(value):
        raise ValueError(f"{path} contains raw secret material")


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, child in value.items():
            normalized = normalize_governance_key(key)
            if (
                normalized in TECHNICAL_PARAMETER_KEYS
                or normalized in _SECRET_KEYS
                or _is_secret_reference_key(normalized)
            ):
                continue
            sanitized[str(key)] = _redact(child)
        return sanitized
    if isinstance(value, list):
        return [_redact(child) for child in value]
    if isinstance(value, str) and _looks_like_raw_secret(value):
        return None
    return value


def redact_hidden_parameters(value: Any) -> Any:
    return _redact(value)


def validate_allowed_keys(
    value: Mapping[str, Any],
    *,
    allowed_keys: set[str],
    path: str,
) -> None:
    unknown = [
        str(key)
        for key in value
        if normalize_governance_key(key) not in allowed_keys
    ]
    if unknown:
        raise ValueError(f"{path} contains unsupported fields: {sorted(unknown)}")


def validate_medical_node_configs(graph: Mapping[str, Any]) -> None:
    nodes = graph.get("nodes", [])
    if not isinstance(nodes, list):
        return
    for index, node in enumerate(nodes):
        if not isinstance(node, Mapping):
            continue
        node_type = normalize_governance_key(node.get("type", ""))
        config = node.get("config", {})
        if not isinstance(config, Mapping):
            continue
        allowed_keys = MEDICAL_NODE_CONFIG_KEYS.get(node_type, set())
        validate_allowed_keys(
            config,
            allowed_keys=allowed_keys,
            path=f"workflow.patch.graph.nodes[{index}].config",
        )
