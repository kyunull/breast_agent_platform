import re
from collections.abc import Mapping
from typing import Any

TECHNICAL_PARAMETER_KEYS = {
    "bm25",
    "deduplication",
    "frequency_penalty",
    "max_tokens",
    "presence_penalty",
    "retries",
    "score_threshold",
    "seed",
    "temperature",
    "timeout",
    "top_k",
    "top_p",
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


def _normalize_key(key: Any) -> str:
    return str(key).lower().replace("-", "_")


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
            normalized = _normalize_key(key)
            child_path = f"{path}.{key}"
            if normalized in _SECRET_KEYS:
                raise ValueError(f"{child_path} must use an environment reference")
            if _is_secret_reference_key(normalized):
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
            normalized = _normalize_key(key)
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
