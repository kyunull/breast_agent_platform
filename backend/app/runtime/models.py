from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.profiles.models import ModelProfile
    from app.users.models import User
    from app.workflows.models import Workflow, WorkflowVersion


def utc_now() -> datetime:
    return datetime.now(UTC)


class WorkflowRun(Base):
    __tablename__ = "workflow_run"
    __table_args__ = (
        CheckConstraint("mode IN ('sync', 'async')", name="ck_workflow_run_mode"),
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="ck_workflow_run_status",
        ),
        Index("ix_workflow_run_workflow_created", "workflow_id", "created_at"),
        Index("ix_workflow_run_created_by", "created_by"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workflow_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflow.id", ondelete="CASCADE"), nullable=False
    )
    workflow_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflow_version.id", ondelete="CASCADE"), nullable=False
    )
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="sync")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    input_summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    output_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    workflow: Mapped["Workflow"] = relationship(foreign_keys=[workflow_id])
    workflow_version: Mapped["WorkflowVersion"] = relationship(foreign_keys=[workflow_version_id])
    creator: Mapped["User | None"] = relationship(foreign_keys=[created_by])
    traces: Mapped[list["NodeTrace"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="NodeTrace.created_at"
    )
    evidence: Mapped[list["RunEvidence"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="RunEvidence.created_at"
    )


class NodeTrace(Base):
    __tablename__ = "node_trace"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'branched', 'insufficient', 'failed', 'cancelled')",
            name="ck_node_trace_status",
        ),
        Index("ix_node_trace_run_created", "run_id", "created_at"),
        Index("ix_node_trace_run_node", "run_id", "node_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflow_run.id", ondelete="CASCADE"), nullable=False
    )
    node_id: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_trace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("node_trace.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    input_summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    output_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    evidence_refs_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    run: Mapped[WorkflowRun] = relationship(back_populates="traces", foreign_keys=[run_id])
    parent_trace: Mapped["NodeTrace | None"] = relationship(
        remote_side=[id], foreign_keys=[parent_trace_id]
    )
    evidence: Mapped[list["RunEvidence"]] = relationship(
        back_populates="trace", cascade="all, delete-orphan", order_by="RunEvidence.created_at"
    )


class RunEvidence(Base):
    __tablename__ = "run_evidence"
    __table_args__ = (
        Index("ix_run_evidence_run", "run_id"),
        Index("ix_run_evidence_trace", "trace_id"),
        Index("ix_run_evidence_evidence_id", "run_id", "evidence_id", unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflow_run.id", ondelete="CASCADE"), nullable=False
    )
    trace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("node_trace.id", ondelete="CASCADE"), nullable=True
    )
    evidence_id: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_chunk_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_title: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    guideline_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    locator: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_level: Mapped[str | None] = mapped_column(String(128), nullable=True)
    open_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    run: Mapped[WorkflowRun] = relationship(back_populates="evidence", foreign_keys=[run_id])
    trace: Mapped["NodeTrace | None"] = relationship(back_populates="evidence", foreign_keys=[trace_id])


class PromptOptimization(Base):
    __tablename__ = "prompt_optimization"
    __table_args__ = (
        CheckConstraint(
            "status IN ('candidate', 'applied', 'rejected')",
            name="ck_prompt_optimization_status",
        ),
        Index("ix_prompt_optimization_workflow_created", "workflow_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workflow_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflow.id", ondelete="CASCADE"), nullable=False
    )
    node_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("workflow_run.id", ondelete="SET NULL"), nullable=True
    )
    original_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    model_profile_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("model_profile.id", ondelete="SET NULL"), nullable=True
    )
    test_input_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result_diff_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="candidate")
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workflow: Mapped["Workflow"] = relationship(foreign_keys=[workflow_id])
    source_run: Mapped["WorkflowRun | None"] = relationship(foreign_keys=[source_run_id])
    model_profile: Mapped["ModelProfile | None"] = relationship(foreign_keys=[model_profile_id])
    creator: Mapped["User | None"] = relationship(foreign_keys=[created_by])
