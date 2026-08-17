import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.governance import validate_governed_payload

_SUPPORTED_PROVIDERS = {"knowledgebase", "openai", "openai_compatible", "local"}
_SECRET_KEYS = {"api_key", "password", "token", "secret", "access_token"}
_SECRET_REF_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*_REF$")


def _validate_technical_config(config: dict[str, Any]) -> dict[str, Any]:
    provider = config.get("provider")
    if provider is not None and provider not in _SUPPORTED_PROVIDERS:
        raise ValueError("unsupported provider")

    top_k = config.get("top_k")
    if top_k is not None and (not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1):
        raise ValueError("top_k must be at least 1")
    score_threshold = config.get("score_threshold")
    if score_threshold is not None and (
        not isinstance(score_threshold, (int, float))
        or isinstance(score_threshold, bool)
        or not 0 <= score_threshold <= 1
    ):
        raise ValueError("score_threshold must be between 0 and 1")
    retries = config.get("retries")
    if retries is not None and (not isinstance(retries, int) or isinstance(retries, bool) or retries < 0):
        raise ValueError("retries must be non-negative")
    timeout = config.get("timeout")
    if timeout is not None and (
        not isinstance(timeout, (int, float))
        or isinstance(timeout, bool)
        or timeout <= 0
    ):
        raise ValueError("timeout must be positive")

    for key, value in config.items():
        normalized = key.lower().replace("-", "_")
        if normalized in _SECRET_KEYS:
            raise ValueError("store secrets as environment references")
        if normalized.endswith("_ref") and (
            not isinstance(value, str) or not _SECRET_REF_PATTERN.fullmatch(value)
        ):
            raise ValueError("secret references must use an uppercase *_REF name")
    validate_governed_payload(config, allow_technical_parameters=True, path="technical_config")
    return config


class ProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    technical_config: dict[str, Any] = Field(default_factory=dict)
    medical_options: dict[str, Any] = Field(default_factory=dict)
    exposed_to_medical: bool = False
    is_active: bool = True

    @model_validator(mode="after")
    def validate_config(self) -> "ProfileCreate":
        _validate_technical_config(self.technical_config)
        validate_governed_payload(
            self.medical_options,
            allow_technical_parameters=False,
            path="medical_options",
        )
        return self


class ProfilePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    technical_config: dict[str, Any] | None = None
    medical_options: dict[str, Any] | None = None
    exposed_to_medical: bool | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_config(self) -> "ProfilePatch":
        if self.technical_config is not None:
            _validate_technical_config(self.technical_config)
        if self.medical_options is not None:
            validate_governed_payload(
                self.medical_options,
                allow_technical_parameters=False,
                path="medical_options",
            )
        return self


class MedicalProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    exposed_to_medical: bool
    medical_options: dict[str, Any]


class AdminProfileRead(MedicalProfileRead):
    technical_config: dict[str, Any]
    is_active: bool
