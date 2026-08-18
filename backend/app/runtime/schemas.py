from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RunCreate(BaseModel):
    workflow_id: str
    version_number: int | None = Field(default=None, ge=0)
    input: dict[str, Any] = Field(default_factory=dict)
    mode: Literal["sync", "async"] = "sync"
    model_profile_id: str | None = None


class RunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    workflow_id: str
    workflow_version_id: str
    model_profile_id: str | None = None
    mode: str
    status: str
    input_sha256: str
    input_summary: dict[str, Any] = Field(validation_alias="input_summary_json")
    output: dict[str, Any] | None = Field(default=None, validation_alias="output_json")
    error: dict[str, Any] | None = Field(default=None, validation_alias="error_json")
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime


class TraceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    run_id: str
    node_id: str
    parent_trace_id: str | None
    status: str
    attempt: int
    input_summary: dict[str, Any] = Field(validation_alias="input_summary_json")
    output: dict[str, Any] | None = Field(default=None, validation_alias="output_json")
    error: dict[str, Any] | None = Field(default=None, validation_alias="error_json")
    evidence_refs: list[str] = Field(validation_alias="evidence_refs_json")
    duration_ms: int | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    trace_id: str | None
    evidence_id: str
    raw_chunk_id: str | None
    text: str
    score: float | None
    source_title: str | None
    guideline_id: str | None
    version_id: str | None
    locator: str | None
    source_level: str | None
    open_url: str | None
    created_at: datetime


class PromptOptimizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    workflow_id: str
    node_id: str
    source_run_id: str | None
    original_prompt: str
    candidate_prompt: str
    instruction: str
    model_profile_id: str | None
    test_input_sha256: str | None
    result_diff: dict[str, Any] = Field(validation_alias="result_diff_json")
    status: str
    created_by: str | None
    created_at: datetime
    applied_at: datetime | None


class PromptOptimizationCreate(BaseModel):
    run_id: str
    node_id: str = Field(min_length=1, max_length=255)
    instruction: str = Field(min_length=1, max_length=4_000)
    model_profile_id: str | None = None


class KnowledgePreviewRequest(BaseModel):
    knowledge_profile_id: str
    query: str = Field(min_length=1, max_length=10_000)
    guideline_ids: list[str] = Field(default_factory=list)
    version_ids: list[str] = Field(default_factory=list)
    language: str = Field(default="zh", min_length=1, max_length=32)


class KnowledgePreviewRead(BaseModel):
    evidence: list[EvidenceRead]
