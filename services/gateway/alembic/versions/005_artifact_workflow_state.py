"""Pipeline V2 artifact workflow state fields.

Revision ID: 005_artifact_workflow_state
Revises: 004_pipeline_v2_run_jobs
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005_artifact_workflow_state"
down_revision: str | None = "004_pipeline_v2_run_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "artifact_workflows",
        sa.Column("contract_revision_id", sa.Integer(), nullable=False, server_default="1"),
        schema="public",
    )
    op.add_column(
        "artifact_workflows",
        sa.Column(
            "research_guidance_id",
            sa.String(64),
            nullable=False,
            server_default="guidance-default",
        ),
        schema="public",
    )
    op.add_column(
        "artifact_workflows",
        sa.Column("validation_status", sa.String(32), nullable=False, server_default="pending"),
        schema="public",
    )
    op.add_column(
        "artifact_workflows",
        sa.Column("judge_status", sa.String(32), nullable=False, server_default="pending"),
        schema="public",
    )
    op.add_column(
        "artifact_workflows",
        sa.Column("snapshot_refs", sa.JSON(), nullable=False, server_default="[]"),
        schema="public",
    )
    op.add_column(
        "artifact_workflows",
        sa.Column("last_error", sa.Text(), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("artifact_workflows", "last_error", schema="public")
    op.drop_column("artifact_workflows", "snapshot_refs", schema="public")
    op.drop_column("artifact_workflows", "judge_status", schema="public")
    op.drop_column("artifact_workflows", "validation_status", schema="public")
    op.drop_column("artifact_workflows", "research_guidance_id", schema="public")
    op.drop_column("artifact_workflows", "contract_revision_id", schema="public")
