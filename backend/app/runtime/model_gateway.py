import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import httpx


class GatewayError(RuntimeError):
    """Provider error safe to persist in a node error summary."""


@dataclass(frozen=True, slots=True)
class ChatCompletionResult:
    content: str
    model: str
    usage: dict[str, int]
    finish_reason: str | None
    response_id: str | None


def resolve_secret_reference(reference: Any, *, required: bool = True) -> str | None:
    if reference in (None, ""):
        if required:
            raise GatewayError("API key environment reference is required")
        return None
    if not isinstance(reference, str) or not reference.endswith("_REF"):
        raise GatewayError("API key must use an uppercase *_REF environment reference")

    configured = os.getenv(reference)
    if configured:
        indirect = os.getenv(configured) if configured.isidentifier() else None
        return indirect or configured
    target_name = reference.removesuffix("_REF")
    secret = os.getenv(target_name)
    if secret:
        return secret
    if required:
        raise GatewayError(f"unresolved API key environment reference: {reference}")
    return None


def _config(profile: Any) -> dict[str, Any]:
    config = getattr(profile, "technical_config_json", None)
    if not isinstance(config, Mapping):
        raise GatewayError("profile technical configuration is missing")
    return dict(config)


def _message_content(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = [part.get("text") for part in value if isinstance(part, Mapping)]
        if parts and all(isinstance(part, str) for part in parts):
            return "".join(parts)
    raise GatewayError("Chat Completions message content must be text")


class OpenAICompatibleGateway:
    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client()

    def complete(
        self,
        profile: Any,
        messages: Sequence[Mapping[str, Any]],
        response_format: Mapping[str, Any] | None = None,
    ) -> ChatCompletionResult:
        config = _config(profile)
        base_url = str(config.get("base_url", "")).rstrip("/")
        model = str(config.get("model") or config.get("model_name") or "")
        if not base_url:
            raise GatewayError("model profile base_url is required")
        if not model:
            raise GatewayError("model profile model is required")

        reference = config.get("api_key_ref")
        api_key = resolve_secret_reference(reference, required=reference is not None)
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload: dict[str, Any] = {"model": model, "messages": [dict(item) for item in messages]}
        for key in ("temperature", "top_p", "max_tokens", "frequency_penalty", "presence_penalty", "seed"):
            if key in config:
                payload[key] = config[key]
        if response_format is not None:
            payload["response_format"] = dict(response_format)

        response = self._post_with_retries(
            f"{base_url}/chat/completions",
            payload,
            headers,
            timeout=float(config.get("timeout", 30)),
            retries=int(config.get("retries", 0)),
        )
        try:
            body = response.json()
        except ValueError as exc:
            raise GatewayError("Chat Completions returned invalid JSON") from exc
        if not isinstance(body, Mapping):
            raise GatewayError("Chat Completions response must be an object")
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise GatewayError("Chat Completions response choices are missing")
        first = choices[0]
        if not isinstance(first, Mapping) or not isinstance(first.get("message"), Mapping):
            raise GatewayError("Chat Completions response message is missing")
        content = _message_content(first["message"].get("content"))
        usage = body.get("usage")
        safe_usage = {
            str(key): int(value)
            for key, value in usage.items()
            if isinstance(usage, Mapping) and isinstance(value, int) and not isinstance(value, bool)
        } if isinstance(usage, Mapping) else {}
        return ChatCompletionResult(
            content=content,
            model=str(body.get("model") or model),
            usage=safe_usage,
            finish_reason=str(first["finish_reason"]) if first.get("finish_reason") is not None else None,
            response_id=str(body["id"]) if body.get("id") is not None else None,
        )

    def _post_with_retries(
        self,
        url: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
        *,
        timeout: float,
        retries: int,
    ) -> httpx.Response:
        last_error: Exception | None = None
        for _ in range(retries + 1):
            try:
                response = self._client.post(url, json=payload, headers=headers, timeout=timeout)
                response.raise_for_status()
                return response
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
        raise GatewayError("model provider request failed") from last_error
