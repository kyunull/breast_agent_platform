import re
from collections.abc import Mapping
from typing import Any

from jsonpath_ng.exceptions import JsonPathLexerError, JsonPathParserError
from jsonpath_ng.ext import parse

from app.extraction.schemas import (
    ArraySelection,
    ExtractionConfig,
    ExtractionField,
    ExtractionPreview,
    SufficiencyResult,
    _parse_order_value,
)

_MISSING = object()
_DOT_FIELD = re.compile(r"\.([^\.\[\]]+)")


def _normalize_path(path: str) -> str:
    """Use bracket fields so JSONPath accepts Unicode and punctuated keys."""
    return _DOT_FIELD.sub(
        lambda match: "['" + match.group(1).replace("'", "\\'") + "']",
        path,
    )


def _jsonpath_matches(payload: Any, path: str) -> list[Any]:
    expression = parse(_normalize_path(path))
    return [match.value for match in expression.find(payload)]


def _filter_value(item: Any, path: str) -> Any:
    if not isinstance(item, Mapping):
        return _MISSING
    if path.startswith("$"):
        matches = _jsonpath_matches(item, path)
    else:
        matches = _jsonpath_matches(item, f"$.{path}")
    return matches[0] if matches else _MISSING


def _matches_filter(item: Any, selection: ArraySelection) -> bool:
    condition = selection.filter
    if not condition:
        return True
    if "field" in condition:
        checks = [condition]
    else:
        checks = [{"field": field, "operator": "eq", "value": expected} for field, expected in condition.items()]
    for check in checks:
        actual = _filter_value(item, str(check.get("field", "")))
        if actual is _MISSING:
            return False
        operator = check.get("operator", "eq")
        expected = check.get("value")
        try:
            if operator == "eq" and actual != expected:
                return False
            if operator == "ne" and actual == expected:
                return False
            if operator == "contains" and str(expected) not in actual:
                return False
            if operator in {"gt", "gte", "lt", "lte"}:
                left = _parse_order_value(actual)
                right = _parse_order_value(expected)
                comparisons = {"gt": left > right, "gte": left >= right, "lt": left < right, "lte": left <= right}
                if not comparisons[operator]:
                    return False
            if operator == "in" and actual not in expected:
                return False
            if operator not in {"eq", "ne", "contains", "gt", "gte", "lt", "lte", "in"}:
                return False
        except (TypeError, ValueError):
            return False
    return True


def _time_in_window(item: Any, selection: ArraySelection) -> bool:
    if not (selection.time_from or selection.time_to):
        return True
    value = _filter_value(item, selection.sort_by or "")
    if value is _MISSING:
        return False
    try:
        current = _parse_order_value(value)
        if selection.time_from is not None and current < _parse_order_value(selection.time_from):
            return False
        return selection.time_to is None or current <= _parse_order_value(selection.time_to)
    except (TypeError, ValueError):
        return False


def _select_array(value: Any, selection: ArraySelection) -> Any:
    values = list(value) if isinstance(value, list) else [value]
    values = [item for item in values if _matches_filter(item, selection) and _time_in_window(item, selection)]
    if selection.sort_by:
        values.sort(
            key=lambda item: _parse_order_value(_filter_value(item, selection.sort_by)),
            reverse=selection.order == "desc",
        )
    if selection.take == "all":
        return values
    if not values:
        return _MISSING
    return values[-1] if selection.take == "latest" else values[0]


def _convert(value: Any, field: ExtractionField) -> Any:
    if field.type == "any":
        return value
    if field.type == "string" and isinstance(value, str):
        return value
    if field.type == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    if field.type == "integer" and isinstance(value, int) and not isinstance(value, bool):
        return value
    if field.type == "boolean" and isinstance(value, bool):
        return value
    if field.type == "object" and isinstance(value, dict):
        return value
    if field.type == "array" and isinstance(value, list):
        return value
    raise TypeError(f"value does not match configured type {field.type}")


def _extract_field(payload: dict[str, Any], field: ExtractionField) -> tuple[Any, str | None]:
    try:
        matches = _jsonpath_matches(payload, field.path)
    except (JsonPathLexerError, JsonPathParserError) as exc:
        return _MISSING, f"invalid JSONPath: {exc}"
    if field.array is not None:
        try:
            if len(matches) == 1 and isinstance(matches[0], list):
                value = _select_array(matches[0], field.array)
            else:
                value = _select_array(matches, field.array)
        except (TypeError, ValueError) as exc:
            return _MISSING, f"array selection failed: {exc}"
    elif not matches:
        value = _MISSING
    elif len(matches) == 1:
        value = matches[0]
    else:
        value = matches
    if value is _MISSING:
        return value, None
    try:
        return _convert(value, field), None
    except TypeError as exc:
        return _MISSING, str(exc)


def preview_extraction(payload: dict[str, Any], config: ExtractionConfig) -> ExtractionPreview:
    groups: dict[str, dict[str, Any]] = {}
    missing: dict[str, list[str]] = {}
    sufficiency: dict[str, SufficiencyResult] = {}
    errors: dict[str, dict[str, str]] = {}
    for group in config.groups:
        values: dict[str, Any] = {}
        group_errors: dict[str, str] = {}
        extracted_aliases: set[str] = set()
        for field in group.fields:
            value, error = _extract_field(payload, field)
            if value is _MISSING:
                if field.default is not None:
                    values[field.alias] = field.default
                if error:
                    group_errors[field.alias] = error
            else:
                values[field.alias] = value
                extracted_aliases.add(field.alias)
        required_aliases = [
            field.alias
            for field in group.fields
            if field.required or field.alias in group.required
        ]
        required_missing = [
            alias for alias in required_aliases if alias not in extracted_aliases
        ]
        groups[group.id] = values
        missing[group.id] = required_missing
        errors[group.id] = group_errors
        sufficiency[group.id] = SufficiencyResult(
            status="sufficient" if not required_missing and not group_errors else "insufficient",
            missing_required=required_missing,
            error_count=len(group_errors),
        )
    return ExtractionPreview(groups=groups, missing=missing, sufficiency=sufficiency, errors=errors)
