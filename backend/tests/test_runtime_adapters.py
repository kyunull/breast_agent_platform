import base64
import json

import httpx
import pytest

from app.runtime.knowledge_gateway import (
    BreastKnowledgebaseAdapter,
    GenericHttpKnowledgeBaseAdapter,
    normalize_knowledge_response,
)
from app.runtime.model_gateway import GatewayError, OpenAICompatibleGateway


class Profile:
    def __init__(self, config):
        self.technical_config_json = config
        self.medical_options_json = {}


def test_openai_gateway_posts_chat_completions_with_encrypted_key():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url == httpx.URL("https://models.example.test/v1/chat/completions")
        assert request.headers["authorization"] == "Bearer test-secret"
        return httpx.Response(
            200,
            json={
                "id": "chat-1",
                "choices": [{"message": {"role": "assistant", "content": '{"ok":true}'}}],
                "usage": {"prompt_tokens": 4, "completion_tokens": 2},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    from app.core.credentials import CredentialManager
    manager = CredentialManager.from_key(base64.urlsafe_b64encode(b"0" * 32))
    encrypted = manager.encrypt_secret("test-secret")
    gateway = OpenAICompatibleGateway(client=client, credential_manager=manager)
    result = gateway.complete(
        Profile(
            {
                "provider": "openai_compatible",
                "base_url": "https://models.example.test/v1",
                "model": "gpt-test",
                "api_key_encrypted": encrypted,
                "temperature": 0.2,
                "top_p": 0.9,
                "max_tokens": 200,
            }
        ),
        [{"role": "user", "content": "hello"}],
        response_format={"type": "json_object"},
    )

    assert result.content == '{"ok":true}'
    assert result.model == "gpt-test"
    assert result.usage == {"prompt_tokens": 4, "completion_tokens": 2}
    assert len(requests) == 1
    assert json.loads(requests[0].content) == {
        "model": "gpt-test",
        "messages": [{"role": "user", "content": "hello"}],
        "temperature": 0.2,
        "top_p": 0.9,
        "max_tokens": 200,
        "response_format": {"type": "json_object"},
    }
    client.close()


def test_openai_gateway_accepts_a_full_chat_completions_url():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    gateway = OpenAICompatibleGateway(client=client)
    gateway.complete(
        Profile(
            {
                "base_url": "https://models.example.test/v1/chat/completions",
                "model": "gpt-test",
            }
        ),
        [{"role": "user", "content": "hello"}],
    )

    assert requests[0].url == httpx.URL("https://models.example.test/v1/chat/completions")
    client.close()


@pytest.mark.parametrize(
    ("status_code", "code", "safe_message"),
    [
        (401, "model_authentication_failed", "API Key 无效或无权访问该模型。"),
        (404, "model_endpoint_not_found", "模型接口地址不正确。"),
        (429, "model_rate_limited", "模型服务请求过于频繁，请稍后重试。"),
        (503, "model_service_unavailable", "模型服务暂时不可用。"),
    ],
)
def test_openai_gateway_classifies_provider_http_errors(status_code, code, safe_message):
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                status_code,
                json={"error": {"message": "do not expose provider response or secrets"}},
            )
        )
    )
    gateway = OpenAICompatibleGateway(client=client)

    with pytest.raises(GatewayError) as caught:
        gateway.complete(
            Profile({"base_url": "https://models.example.test/v1", "model": "gpt-test"}),
            [],
        )

    assert caught.value.code == code
    assert caught.value.safe_message == safe_message
    assert "do not expose" not in caught.value.safe_message
    client.close()


def test_openai_gateway_rejects_environment_key_reference():
    gateway = OpenAICompatibleGateway(client=httpx.Client(transport=httpx.MockTransport(lambda _: None)))
    with pytest.raises(GatewayError, match="directly configured"):
        gateway.complete(
            Profile(
                {
                    "base_url": "https://models.example.test/v1",
                    "model": "gpt-test",
                    "api_key_ref": "MODEL_API_KEY_REF",
                }
            ),
            [],
        )


def test_openai_gateway_normalizes_malformed_response():
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"choices": []}))
    )
    gateway = OpenAICompatibleGateway(client=client)
    with pytest.raises(GatewayError, match="choices"):
        gateway.complete(
            Profile({"base_url": "https://models.example.test", "model": "gpt-test"}),
            [],
        )


def test_breast_knowledgebase_normalizes_evidence_and_sends_filters(monkeypatch):
    monkeypatch.setenv("KB_API_KEY", "kb-test-secret")
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "evidence": [
                    {
                        "text": "HER2 阳性晚期乳腺癌推荐方案。",
                        "raw_chunk_id": "chunk-7",
                        "score": 0.93,
                        "guideline_id": "caca",
                        "version_id": "caca-v3",
                        "authority_level": "primary_guideline",
                        "citation": {"title": "指南原文", "page": 12},
                    }
                ],
                "resolved_version_ids": ["caca-v3"],
            },
        )

    adapter = BreastKnowledgebaseAdapter(
        Profile(
            {
                "base_url": "http://knowledgebase.test",
                "search_path": "/search",
                "top_k": 5,
                "bm25": True,
                "api_key_ref": "KB_API_KEY_REF",
            }
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    records = adapter.search(
        "HER2 阳性晚期乳腺癌",
        {"guideline_ids": ["caca"], "version_ids": ["caca-v3"], "language": "zh"},
    )

    assert len(records) == 1
    assert records[0].evidence_id
    assert records[0].raw_chunk_id == "chunk-7"
    assert records[0].text.startswith("HER2")
    assert records[0].source_title == "指南原文"
    assert records[0].locator == "page 12"
    assert records[0].source_level == "primary_guideline"
    assert json.loads(requests[0].content) == {
        "query": "HER2 阳性晚期乳腺癌",
        "guideline_ids": ["caca"],
        "version_ids": ["caca-v3"],
        "language": "zh",
        "top_k": 5,
        "use_bm25": True,
    }
    assert requests[0].headers["authorization"] == "Bearer kb-test-secret"


def test_generic_adapter_uses_configured_field_mapping():
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "content": "Evidence",
                            "id": "a-1",
                            "similarity": 0.7,
                            "title": "Source",
                            "url": "https://source.test/a-1",
                        }
                    ]
                },
            )
        )
    )
    adapter = GenericHttpKnowledgeBaseAdapter(
        Profile(
            {
                "base_url": "http://generic.test",
                "search_path": "/retrieve",
                "result_path": "items",
                "field_mapping": {
                    "text": "content",
                    "raw_chunk_id": "id",
                    "score": "similarity",
                    "source_title": "title",
                    "open_url": "url",
                },
            }
        ),
        client=client,
    )
    records = adapter.search("query", {})
    assert records[0].raw_chunk_id == "a-1"
    assert records[0].open_url == "https://source.test/a-1"


def test_normalize_knowledge_response_rejects_missing_text():
    with pytest.raises(GatewayError, match="text"):
        normalize_knowledge_response({"evidence": [{"score": 0.2}]})
