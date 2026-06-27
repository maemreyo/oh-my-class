"""Pipeline V2 durable run jobs.

Revision ID: 004_pipeline_v2_run_jobs
Revises: 003_pipeline_v2_control_tables
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004_pipeline_v2_run_jobs"
down_revision: str | None = "003_pipeline_v2_control_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "run_jobs",
        sa.Column("job_id", sa.String(64), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(64),
            sa.ForeignKey("public.runs.run_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("lease_owner", sa.String(128), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("idempotency_key", name="uq_run_jobs_idempotency_key"),
        schema="public",
    )
    op.create_index(
        "ix_run_jobs_status_created_at",
        "run_jobs",
        ["status", "created_at"],
        schema="public",
    )
    op.create_index("ix_run_jobs_run_id", "run_jobs", ["run_id"], schema="public")


def downgrade() -> None:
    op.drop_index("ix_run_jobs_run_id", table_name="run_jobs", schema="public")
    op.drop_index("ix_run_jobs_status_created_at", table_name="run_jobs", schema="public")
    op.drop_table("run_jobs", schema="public")
