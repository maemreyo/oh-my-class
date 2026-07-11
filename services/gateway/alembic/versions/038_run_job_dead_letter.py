"""#124: dead-letter metadata columns on run_jobs.

Revision ID: 038_run_job_dead_letter
Revises: 037_fix_fk_ondelete_drift
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "038_run_job_dead_letter"
down_revision: str | None = "037_fix_fk_ondelete_drift"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("run_jobs", schema="public")}
    if "last_error" not in columns:
        op.add_column("run_jobs", sa.Column("last_error", sa.Text(), nullable=True), schema="public")
    if "error_classification" not in columns:
        op.add_column(
            "run_jobs", sa.Column("error_classification", sa.String(32), nullable=True), schema="public",
        )
    if "dead_lettered_at" not in columns:
        op.add_column(
            "run_jobs", sa.Column("dead_lettered_at", sa.DateTime(timezone=True), nullable=True), schema="public",
        )


def downgrade() -> None:
    op.drop_column("run_jobs", "dead_lettered_at", schema="public")
    op.drop_column("run_jobs", "error_classification", schema="public")
    op.drop_column("run_jobs", "last_error", schema="public")
