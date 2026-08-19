import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.governance import (
    MEDICAL_PROFILE_OPTION_KEYS,
    normalize_governance_key,
    validate_allowed_keys,
    validate_governed_payload,
)

_SUPPORTED_PROVIDERS = {
    "knowledgebase",
    "generic_http",
    "http",
    "openai",
    "openai_compatible",
    "local",
}
_SECRET_KEYS = {"api_key", "password", "token", "secret", "access_token"}
_SECRET_REF_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*_REF$")


def _validate_technical_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized_config: dict[str, Any] = {}
    for key, value in config.items():
        normalized = normalize_governance_key(key)
        if normalized in normalized_config:
            raise ValueError(f"duplicate technical configuration field: {normalized}")
        normalized_config[normalized] = value

    provider = normalized_config.get("provider")
    if provider is not None and (
        not isinstance(provider, str) or provider not in _SUPPORTED_PROVIDERS
    ):
        raise ValueError("unsupported provider")

    top_k = normalized_config.get("top_k")
    if top_k is not None and (not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1):
        raise ValueError("top_k must be at least 1")
    score_threshold = normalized_config.get("score_threshold")
    if score_threshold is not None and (
        not isinstance(score_threshold, (int, float))
        or isinstance(score_threshold, bool)
        or not 0 <= score_threshold <= 1
    ):
        raise ValueError("score_threshold must be between 0 and 1")
    retries = normalized_config.get("retries")
    if retries is not None and (not isinstance(retries, int) or isinstance(retries, bool) or retries < 0):
        raise ValueError("retries must be non-negative")
    timeout = normalized_config.get("timeout")
    if timeout is not None and (
        not isinstance(timeout, (int, float))
        or isinstance(timeout, bool)
        or timeout <= 0
    ):
        raise ValueError("timeout must be positive")

    for key, value in normalized_config.items():
        if key in _SECRET_KEYS:
            raise ValueError("store secrets as environment references")
        if key.endswith("_ref") and (
            not isinstance(value, str) or not _SECRET_REF_PATTERN.fullmatch(value)
        ):
            raise ValueError("secret references must use an uppercase *_REF name")
    validate_governed_payload(
        normalized_config,
        allow_technical_parameters=True,
        path="technical_config",
    )
    return normalized_config


class ProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    technical_config: dict[str, Any] = Field(default_factory=dict)
    medical_options: dict[str, Any] = Field(default_factory=dict)
    exposed_to_medical: bool = False
    is_active: bool = True

    @model_validator(mode="after")
    def validate_config(self) -> "ProfileCreate":
        self.technical_config = _validate_technical_config(self.technical_config)
        validate_allowed_keys(
            self.medical_options,
            allowed_keys=MEDICAL_PROFILE_OPTION_KEYS,
            path="medical_options",
        )
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
            self.technical_config = _validate_technical_config(self.technical_config)
        if self.medical_options is not None:
            validate_allowed_keys(
                self.medical_options,
                allowed_keys=MEDICAL_PROFILE_OPTION_KEYS,
                path="medical_options",
            )
            validate_governed_payload(
                self.medical_options,
                allow_technical_parameters=False,
                path="medical_options",
            )
        return self


class ModelProfileConnectionTest(BaseModel):
    technical_config: dict[str, Any]

    @model_validator(mode="after")
    def validate_config(self) -> "ModelProfileConnectionTest":
        self.technical_config = _validate_technical_config(self.technical_config)
        if self.technical_config.get("provider") != "openai_compatible":
            raise ValueError("provider must be openai_compatible")
        if not isinstance(self.technical_config.get("base_url"), str) or not self.technical_config[
            "base_url"
        ].strip():
            raise ValueError("base_url is required")
        model = self.technical_config.get("model") or self.technical_config.get("model_name")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model or model_name is required")
        return self


class ModelProfileConnectionTestRead(BaseModel):
    ok: bool = True
    model: str
    latency_ms: int = Field(ge=0)


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
