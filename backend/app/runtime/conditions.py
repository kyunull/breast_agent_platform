from dataclasses import dataclass
from typing import Any

from app.runtime.context import ExecutionContext


class _Missing:
    pass


MISSING = _Missing()


@dataclass(frozen=True, slots=True)
class ConditionResult:
    status: str
    selected_ports: list[str]
    value: bool | None


def resolve_value(value: Any, context: ExecutionContext) -> Any:
    if not isinstance(value, str):
        return value
    if value.startswith("{{") and value.endswith("}}"):
        value = value[2:-2].strip()
    value = value.removeprefix("$")
    parts = value.split(".") if value else []
    if len(parts) <= 1 and value not in {"extracted", "raw_input", "node_outputs"}:
        return value
    roots: dict[str, Any] = {
        "extracted": context.extracted,
        "raw_input": context.raw_input,
        "input": context.extracted,
        "node_outputs": context.node_outputs,
        "nodes": context.node_outputs,
    }
    if parts and parts[0] in roots:
        current = roots[parts.pop(0)]
    elif parts and parts[0] in context.extracted:
        current = context.extracted[parts.pop(0)]
    elif parts and parts[0] in context.node_outputs:
        current = context.node_outputs[parts.pop(0)]
    else:
        return value
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return MISSING
    return current


def _evaluate(config: Any, context: ExecutionContext) -> str:
    if not isinstance(config, dict):
        value = resolve_value(config, context)
        if value is MISSING:
            return "unknown"
        return "true" if bool(value) else "false"
    operator = str(config.get("operator", "exists")).lower()
    if operator in {"and", "or"}:
        statuses = [_evaluate(item, context) for item in config.get("operands", [])]
        if operator == "and":
            if "false" in statuses:
                return "false"
            return "unknown" if "unknown" in statuses else "true"
        if "true" in statuses:
            return "true"
        return "unknown" if "unknown" in statuses else "false"
    if operator == "not":
        status = _evaluate(config.get("operand", config.get("value")), context)
        return {"true": "false", "false": "true"}.get(status, "unknown")

    left = resolve_value(config.get("left", config.get("value", MISSING)), context)
    exists = left is not MISSING
    if operator == "exists":
        return "true" if exists else "false"
    if operator == "empty":
        if not exists:
            return "unknown"
        return "true" if left is None or left == "" or left == [] or left == {} else "false"
    if operator == "not_empty":
        if not exists:
            return "unknown"
        return "false" if left is None or left == "" or left == [] or left == {} else "true"
    if not exists:
        return "unknown"
    right = resolve_value(config.get("right"), context)
    if right is MISSING:
        return "unknown"
    if isinstance(right, str):
        if isinstance(left, bool) and right.lower() in {"true", "false"}:
            right = right.lower() == "true"
        elif isinstance(left, (int, float)) and not isinstance(left, bool):
            try:
                right = float(right)
            except ValueError:
                pass
    try:
        if operator in {"eq", "=="}:
            outcome = left == right
        elif operator in {"neq", "ne", "!=", "not_eq"}:
            outcome = left != right
        elif operator == "contains":
            outcome = right in left
        elif operator == "gt":
            outcome = left > right
        elif operator == "lt":
            outcome = left < right
        elif operator == "gte":
            outcome = left >= right
        elif operator == "lte":
            outcome = left <= right
        else:
            return "unknown"
    except (TypeError, ValueError):
        return "unknown"
    return "true" if outcome else "false"


def evaluate_condition(config: dict[str, Any], context: ExecutionContext) -> ConditionResult:
    status = _evaluate(config, context)
    if status == "unknown":
        strategy = str(config.get("missing_strategy", "unknown")).lower()
        if strategy == "false":
            status = "false"
        elif strategy == "needs_review":
            status = "needs_review"
        elif strategy == "error":
            raise ValueError("condition value is unknown")
    value = {"true": True, "false": False}.get(status)
    if status == "true":
        port = str(config.get("true_port", config.get("success_port", "true")))
    elif status in {"false", "needs_review"}:
        port = str(config.get("false_port", config.get("failure_port", "false")))
    else:
        port = str(config.get("unknown_port", "unknown"))
    return ConditionResult(status=status, selected_ports=[port], value=value)
