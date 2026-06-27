"""Soft-delete columns and retention config for pipeline runs.

Revision ID: 007_soft_delete_and_retention
Revises: 006_rendered_snapshot_metadata
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007_soft_delete_and_retention"
down_revision: str | None = "006_rendered_snapshot_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.add_column(
        "runs",
        sa.Column("deleted_by", sa.String(64), nullable=True),
        schema="public",
    )
    op.add_column(
        "runs",
        sa.Column("retention_days", sa.Integer, nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_runs_deleted_at",
        "runs",
        ["deleted_at"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_runs_deleted_at", schema="public")
    op.drop_column("runs", "retention_days", schema="public")
    op.drop_column("runs", "deleted_by", schema="public")
    op.drop_column("runs", "deleted_at", schema="public")
