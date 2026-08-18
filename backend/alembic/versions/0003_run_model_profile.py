"""persist selected run model profile

Revision ID: 0003_run_model_profile
Revises: 0002_runtime_execution
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_run_model_profile"
down_revision: str | Sequence[str] | None = "0002_runtime_execution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("workflow_run") as batch_op:
        batch_op.add_column(sa.Column("model_profile_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_workflow_run_model_profile_id",
            "model_profile",
            ["model_profile_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_workflow_run_model_profile", ["model_profile_id"])


def downgrade() -> None:
    with op.batch_alter_table("workflow_run") as batch_op:
        batch_op.drop_index("ix_workflow_run_model_profile")
        batch_op.drop_constraint("fk_workflow_run_model_profile_id", type_="foreignkey")
        batch_op.drop_column("model_profile_id")
