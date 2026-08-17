from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session

from app.audit.models import AuditLog


_SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "token",
    "api_key",
    "apikey",
    "secret",
    "credential",
    "database_url",
    "db_url",
    "patient_json",
    "patient_data",
    "patient",
    "payload",
    "clinical_record",
    "full_patient",
    "raw_json",
)


def _is_sensitive_key(key: object) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _sanitize_metadata(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _sanitize_metadata(item)
            for key, item in value.items()
            if not _is_sensitive_key(key)
        }
    if isinstance(value, list):
        return [_sanitize_metadata(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_metadata(item) for item in value]
    return value


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
