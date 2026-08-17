from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.extraction.schemas import ExtractionConfig
from app.graph.schemas import WorkflowGraph


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class WorkflowDraftPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    graph: dict[str, Any] | WorkflowGraph | None = None
    extraction: ExtractionConfig | None = None
    metadata: dict[str, Any] | None = None
    template_refs: list[str] | None = None


class WorkflowRead(BaseModel):
    id: str
    owner_id: str | None
    name: str
    description: str | None
    draft_version_number: int


class DraftRead(BaseModel):
    id: str
    workflow_id: str
    version_number: int
    status: str
    name: str
    description: str | None
    graph: dict[str, Any]
    extraction: dict[str, Any]
    metadata: dict[str, Any]
    template_refs: list[str]
    definition_sha256: str | None


class PublishedVersionRead(BaseModel):
    id: str
    workflow_id: str
    version_number: int
    status: str
    definition: dict[str, Any]
    extraction: dict[str, Any]
    definition_sha256: str | None
    created_at: datetime
