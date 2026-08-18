import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

import httpx

from app.runtime.model_gateway import GatewayError, resolve_secret_reference


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    evidence_id: str
    raw_chunk_id: str | None
    text: str
    score: float | None = None
    source_title: str | None = None
    guideline_id: str | None = None
    version_id: str | None = None
    locator: str | None = None
    source_level: str | None = None
    open_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _stable_evidence_id(item: Mapping[str, Any]) -> str:
    identity = {
        "raw_chunk_id": item.get("raw_chunk_id"),
        "guideline_id": item.get("guideline_id"),
        "version_id": item.get("version_id"),
        "text": item.get("text"),
    }
    canonical = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "ev_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


def _citation_fields(citation: Any) -> tuple[str | None, str | None, str | None]:
    if isinstance(citation, str):
        return citation, None, None
    if not isinstance(citation, Mapping):
        return None, None, None
    title = citation.get("title") or citation.get("source_title")
    locator = citation.get("locator")
    if locator is None and citation.get("page") is not None:
        locator = f"page {citation['page']}"
    if locator is None and citation.get("section") is not None:
        locator = f"section {citation['section']}"
    open_url = citation.get("open_url") or citation.get("url")
    return (
        str(title) if title is not None else None,
        str(locator) if locator is not None else None,
        str(open_url) if open_url is not None else None,
    )


def _normalize_item(item: Mapping[str, Any]) -> EvidenceRecord:
    text = item.get("text")
    if not isinstance(text, str) or not text.strip():
        raise GatewayError("knowledge evidence text is missing")
    source_title, citation_locator, citation_url = _citation_fields(item.get("citation"))
    raw_score = item.get("score")
    score = float(raw_score) if isinstance(raw_score, (int, float)) and not isinstance(raw_score, bool) else None
    normalized: dict[str, Any] = {
        "raw_chunk_id": str(item["raw_chunk_id"]) if item.get("raw_chunk_id") is not None else None,
        "text": text,
        "score": score,
        "source_title": item.get("source_title") or source_title,
        "guideline_id": item.get("guideline_id"),
        "version_id": item.get("version_id"),
        "locator": item.get("locator") or citation_locator,
        "source_level": item.get("source_level") or item.get("authority_level"),
        "open_url": item.get("open_url") or citation_url,
    }
    evidence_id = str(item.get("evidence_id") or _stable_evidence_id(normalized))
    return EvidenceRecord(evidence_id=evidence_id, **normalized)


def normalize_knowledge_response(payload: Any) -> list[EvidenceRecord]:
    if not isinstance(payload, Mapping):
        raise GatewayError("knowledge response must be an object")
    items = payload.get("evidence")
    if not isinstance(items, list):
        raise GatewayError("knowledge response evidence must be a list")
    if not all(isinstance(item, Mapping) for item in items):
        raise GatewayError("knowledge evidence entries must be objects")
    return [_normalize_item(item) for item in items]


def _profile_config(profile: Any) -> dict[str, Any]:
    config = getattr(profile, "technical_config_json", None)
    if not isinstance(config, Mapping):
        raise GatewayError("knowledge profile technical configuration is missing")
    return dict(config)


def _lookup(item: Mapping[str, Any], path: str) -> Any:
    value: Any = item
    for part in path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return None
        value = value[part]
    return value


def _lookup_payload(payload: Mapping[str, Any], path: str) -> Any:
    return _lookup(payload, path) if path else payload


class _HttpKnowledgeAdapter:
    def __init__(self, profile: Any, *, client: httpx.Client | None = None) -> None:
        self.profile = profile
        self.config = _profile_config(profile)
        self.client = client or httpx.Client()

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        reference = self.config.get("api_key_ref")
        if reference is not None:
            secret = resolve_secret_reference(reference)
            headers["Authorization"] = f"Bearer {secret}"
        return headers

    def _post(self, payload: Mapping[str, Any]) -> Any:
        base_url = str(self.config.get("base_url", "")).rstrip("/")
        if not base_url:
            raise GatewayError("knowledge profile base_url is required")
        path = str(self.config.get("search_path", "/search"))
        if not path.startswith("/"):
            path = "/" + path
        try:
            response = self.client.post(
                base_url + path,
                json=payload,
                headers=self._headers(),
                timeout=float(self.config.get("timeout", 30)),
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise GatewayError("knowledge provider request failed") from exc


class BreastKnowledgebaseAdapter(_HttpKnowledgeAdapter):
    def search(self, query: str, filters: Mapping[str, Any] | None = None) -> list[EvidenceRecord]:
        filters = filters or {}
        payload = {
            "query": query,
            "guideline_ids": list(filters.get("guideline_ids", [])),
            "version_ids": list(filters.get("version_ids", [])),
            "language": str(filters.get("language", "zh")),
            "top_k": int(self.config.get("top_k", 5)),
            "use_bm25": bool(self.config.get("bm25", False)),
        }
        return normalize_knowledge_response(self._post(payload))


class GenericHttpKnowledgeBaseAdapter(_HttpKnowledgeAdapter):
    def search(self, query: str, filters: Mapping[str, Any] | None = None) -> list[EvidenceRecord]:
        filters = filters or {}
        query_field = str(self.config.get("query_field", "query"))
        request_payload = {query_field: query, **dict(filters)}
        if "top_k" in self.config:
            request_payload.setdefault("top_k", self.config["top_k"])
        response = self._post(request_payload)
        if not isinstance(response, Mapping):
            raise GatewayError("knowledge response must be an object")
        items = _lookup_payload(response, str(self.config.get("result_path", "evidence")))
        if not isinstance(items, list) or not all(isinstance(item, Mapping) for item in items):
            raise GatewayError("configured knowledge result path must contain a list")
        mapping = self.config.get("field_mapping", {})
        if not isinstance(mapping, Mapping):
            raise GatewayError("knowledge field_mapping must be an object")
        normalized_items = []
        fields = (
            "evidence_id",
            "raw_chunk_id",
            "text",
            "score",
            "source_title",
            "guideline_id",
            "version_id",
            "locator",
            "source_level",
            "open_url",
            "citation",
        )
        for item in items:
            normalized_items.append(
                {
                    field: _lookup(item, str(mapping.get(field, field)))
                    for field in fields
                    if _lookup(item, str(mapping.get(field, field))) is not None
                }
            )
        return normalize_knowledge_response({"evidence": normalized_items})
