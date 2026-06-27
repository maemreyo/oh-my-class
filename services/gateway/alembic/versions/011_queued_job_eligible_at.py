"""Add eligible_at column and claim index for queued backpressure.

Revision ID: 011_queued_job_eligible_at
Revises: 010_run_budget_ledgers
Create Date: 2026-06-27

Adds the ``eligible_at`` nullable timestamptz column and the composite
index ``(status, eligible_at)`` to ``public.run_jobs``.  These support
the queued/delayed backpressure state introduced in task 9 where jobs
with ``RunJobStatus.QUEUED`` carry an ``eligible_at`` timestamp that
must be reached before the job becomes claimable.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "011_queued_job_eligible_at"
down_revision: str | None = "010_run_budget_ledgers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "run_jobs",
        sa.Column("eligible_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_run_jobs_status_eligible_at",
        "run_jobs",
        ["status", "eligible_at"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_run_jobs_status_eligible_at",
        table_name="run_jobs",
        schema="public",
    )
    op.drop_column("run_jobs", "eligible_at", schema="public")
