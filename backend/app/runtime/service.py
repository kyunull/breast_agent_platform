import hashlib
import json
from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session

from app.runtime.models import NodeTrace, PromptOptimization, RunEvidence, WorkflowRun

_MAX_SUMMARY_CHARS = 1000
_MAX_DEPTH = 5
_SENSITIVE_KEY_PARTS = ("病历", "原文", "患者数据", "raw", "record", "clinical_text", "medical_text")


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered or part in key for part in _SENSITIVE_KEY_PARTS)


def summarize_input(value: Any, *, max_chars: int = _MAX_SUMMARY_CHARS) -> dict[str, Any]:
    """Return a bounded, structural summary without persisting patient text."""

    def visit(item: Any, depth: int = 0) -> Any:
        if depth >= _MAX_DEPTH:
            return "[truncated]"
        if isinstance(item, Mapping):
            result: dict[str, Any] = {}
            for raw_key, raw_value in list(item.items())[:50]:
                key = str(raw_key)
                if _is_sensitive_key(key):
                    continue
                result[key] = visit(raw_value, depth + 1)
            return result
        if isinstance(item, list):
            return [visit(entry, depth + 1) for entry in item[:20]]
        if isinstance(item, tuple):
            return [visit(entry, depth + 1) for entry in item[:20]]
        if isinstance(item, str):
            return item if len(item) <= 120 else f"[text:{len(item)} chars]"
        if item is None or isinstance(item, (bool, int, float)):
            return item
        return str(item)[:120]

    summary = visit(value)
    if not isinstance(summary, dict):
        summary = {"value": summary}
    encoded = json.dumps(summary, ensure_ascii=False, separators=(",", ":"))
    if len(encoded) <= max_chars:
        return summary
    return {"_summary": "[bounded]", "keys": list(summary)[:30], "chars": len(encoded)}


def input_sha256(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def create_run(
    db: Session,
    workflow: Any,
    version: Any,
    actor_id: str | None,
    payload: Mapping[str, Any],
) -> WorkflowRun:
    raw_input = payload.get("input", {})
    mode = str(payload.get("mode", "sync"))
    if mode not in {"sync", "async"}:
        raise ValueError("mode must be sync or async")
    run = WorkflowRun(
        workflow_id=workflow.id,
        workflow_version_id=version.id,
        mode=mode,
        status="queued",
        input_sha256=input_sha256(raw_input),
        input_summary_json=summarize_input(raw_input),
        created_by=actor_id,
    )
    db.add(run)
    return run


def append_trace(db: Session, run_id: str, trace_data: Mapping[str, Any]) -> NodeTrace:
    trace = NodeTrace(
        run_id=run_id,
        node_id=str(trace_data.get("node_id", "")),
        parent_trace_id=trace_data.get("parent_trace_id"),
        status=str(trace_data.get("status", "queued")),
        attempt=int(trace_data.get("attempt", 1)),
        input_summary_json=dict(trace_data.get("input_summary", {})),
        output_json=trace_data.get("output"),
        error_json=trace_data.get("error"),
        evidence_refs_json=list(trace_data.get("evidence_refs", [])),
        duration_ms=trace_data.get("duration_ms"),
        started_at=trace_data.get("started_at"),
        finished_at=trace_data.get("finished_at"),
    )
    db.add(trace)
    db.flush()
    return trace


def store_evidence(
    db: Session,
    run_id: str,
    trace_id: str | None,
    evidence: Mapping[str, Any],
) -> RunEvidence:
    record = RunEvidence(
        run_id=run_id,
        trace_id=trace_id,
        evidence_id=str(evidence["evidence_id"]),
        raw_chunk_id=evidence.get("raw_chunk_id"),
        text=str(evidence.get("text", "")),
        score=evidence.get("score"),
        source_title=evidence.get("source_title"),
        guideline_id=evidence.get("guideline_id"),
        version_id=evidence.get("version_id"),
        locator=evidence.get("locator"),
        source_level=evidence.get("source_level"),
        open_url=evidence.get("open_url"),
    )
    db.add(record)
    return record


def get_prompt_optimization(db: Session, optimization_id: str) -> PromptOptimization | None:
    return db.get(PromptOptimization, optimization_id)
