import re
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.audit.models import AuditLog

_UUID_METADATA_KEYS = {
    "actor_id",
    "entity_id",
    "profile_id",
    "model_profile_id",
    "knowledge_profile_id",
    "workflow_id",
    "version_id",
    "template_id",
}
_STATUS_VALUES = {"draft", "published", "archived", "active", "inactive"}
_FIELD_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?i)(password|passwd|token|api[\s_-]?key|secret|credential|"
    r"database[\s_-]?(url|user|password|credential)|bearer|"
    r"(?:postgres(?:ql)?|sqlite)://)"
)
_DROP = object()


def _is_sensitive_string(value: str) -> bool:
    return bool(_SENSITIVE_VALUE_PATTERN.search(value))


def _sanitize_uuid(value: Any) -> str | object:
    if not isinstance(value, str) or _is_sensitive_string(value):
        return _DROP
    try:
        return str(UUID(value))
    except ValueError:
        return _DROP


def _sanitize_changed_fields(value: Any) -> list[str] | object:
    if not isinstance(value, (list, tuple)):
        return _DROP

    fields = [
        field
        for field in value
        if isinstance(field, str)
        and _FIELD_NAME_PATTERN.fullmatch(field)
        and not _is_sensitive_string(field)
    ]
    return fields if fields else _DROP


def _sanitize_metadata_value(key: str, value: Any) -> Any:
    if key in _UUID_METADATA_KEYS:
        return _sanitize_uuid(value)
    if key == "changed_fields":
        return _sanitize_changed_fields(value)
    if key == "version_number":
        return (
            value
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0
            else _DROP
        )
    if key == "status":
        return value if isinstance(value, str) and value in _STATUS_VALUES else _DROP
    return _DROP


def _sanitize_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        normalized_key = str(key).lower().replace("-", "_")
        safe_value = _sanitize_metadata_value(normalized_key, value)
        if safe_value is not _DROP:
            sanitized[normalized_key] = safe_value
    return sanitized


def record_audit(
    db: Session,
    actor_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str,
    metadata: Mapping[str, Any] | None = None,
) -> AuditLog:
    audit = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=_sanitize_metadata(metadata or {}),
    )
    db.add(audit)
    db.flush()
    return audit
