"""add deterministic node trace order

Revision ID: 0004_trace_sequence
Revises: 0003_run_model_profile
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_trace_sequence"
down_revision: str | Sequence[str] | None = "0003_run_model_profile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("node_trace") as batch_op:
        batch_op.add_column(
            sa.Column("sequence", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.create_index("ix_node_trace_run_sequence", ["run_id", "sequence"])


def downgrade() -> None:
    with op.batch_alter_table("node_trace") as batch_op:
        batch_op.drop_index("ix_node_trace_run_sequence")
        batch_op.drop_column("sequence")
