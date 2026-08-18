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


def test_openai_gateway_posts_chat_completions_with_env_key(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "test-secret")
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
    gateway = OpenAICompatibleGateway(client=client)
    result = gateway.complete(
        Profile(
            {
                "provider": "openai_compatible",
                "base_url": "https://models.example.test/v1",
                "model": "gpt-test",
                "api_key_ref": "MODEL_API_KEY_REF",
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


def test_openai_gateway_requires_resolvable_key(monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    gateway = OpenAICompatibleGateway(client=httpx.Client(transport=httpx.MockTransport(lambda _: None)))
    with pytest.raises(GatewayError, match="environment reference"):
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
