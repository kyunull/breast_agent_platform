"""runtime workflow execution persistence

Revision ID: 0002_runtime_execution
Revises: 9f65847b8a9e
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_runtime_execution"
down_revision: str | Sequence[str] | None = "9f65847b8a9e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workflow_run",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workflow_id", sa.String(length=36), nullable=False),
        sa.Column("workflow_version_id", sa.String(length=36), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("input_sha256", sa.String(length=64), nullable=False),
        sa.Column("input_summary_json", sa.JSON(), nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=True),
        sa.Column("error_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("mode IN ('sync', 'async')", name="ck_workflow_run_mode"),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="ck_workflow_run_status",
        ),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflow.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_version_id"], ["workflow_version.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["app_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_run_workflow_created", "workflow_run", ["workflow_id", "created_at"])
    op.create_index("ix_workflow_run_created_by", "workflow_run", ["created_by"])

    op.create_table(
        "node_trace",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=False),
        sa.Column("parent_trace_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("input_summary_json", sa.JSON(), nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=True),
        sa.Column("error_json", sa.JSON(), nullable=True),
        sa.Column("evidence_refs_json", sa.JSON(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'branched', 'insufficient', 'failed', 'cancelled')",
            name="ck_node_trace_status",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["workflow_run.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_trace_id"], ["node_trace.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_node_trace_run_created", "node_trace", ["run_id", "created_at"])
    op.create_index("ix_node_trace_run_node", "node_trace", ["run_id", "node_id"])

    op.create_table(
        "run_evidence",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("trace_id", sa.String(length=36), nullable=True),
        sa.Column("evidence_id", sa.String(length=255), nullable=False),
        sa.Column("raw_chunk_id", sa.String(length=255), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("source_title", sa.String(length=1000), nullable=True),
        sa.Column("guideline_id", sa.String(length=255), nullable=True),
        sa.Column("version_id", sa.String(length=255), nullable=True),
        sa.Column("locator", sa.String(length=1000), nullable=True),
        sa.Column("source_level", sa.String(length=128), nullable=True),
        sa.Column("open_url", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["workflow_run.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trace_id"], ["node_trace.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_run_evidence_run", "run_evidence", ["run_id"])
    op.create_index("ix_run_evidence_trace", "run_evidence", ["trace_id"])
    op.create_index("ix_run_evidence_evidence_id", "run_evidence", ["run_id", "evidence_id"], unique=True)

    op.create_table(
        "prompt_optimization",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workflow_id", sa.String(length=36), nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=False),
        sa.Column("source_run_id", sa.String(length=36), nullable=True),
        sa.Column("original_prompt", sa.Text(), nullable=False),
        sa.Column("candidate_prompt", sa.Text(), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("model_profile_id", sa.String(length=36), nullable=True),
        sa.Column("test_input_sha256", sa.String(length=64), nullable=True),
        sa.Column("result_diff_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('candidate', 'applied', 'rejected')",
            name="ck_prompt_optimization_status",
        ),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflow.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_run_id"], ["workflow_run.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["model_profile_id"], ["model_profile.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["app_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prompt_optimization_workflow_created", "prompt_optimization", ["workflow_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_prompt_optimization_workflow_created", table_name="prompt_optimization")
    op.drop_table("prompt_optimization")
    op.drop_index("ix_run_evidence_evidence_id", table_name="run_evidence")
    op.drop_index("ix_run_evidence_trace", table_name="run_evidence")
    op.drop_index("ix_run_evidence_run", table_name="run_evidence")
    op.drop_table("run_evidence")
    op.drop_index("ix_node_trace_run_node", table_name="node_trace")
    op.drop_index("ix_node_trace_run_created", table_name="node_trace")
    op.drop_table("node_trace")
    op.drop_index("ix_workflow_run_created_by", table_name="workflow_run")
    op.drop_index("ix_workflow_run_workflow_created", table_name="workflow_run")
    op.drop_table("workflow_run")
