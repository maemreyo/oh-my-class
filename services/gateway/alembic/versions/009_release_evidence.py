"""Create release_evidence table for production-readiness audit records.

Revision ID: 009_release_evidence
Revises: 007_soft_delete_and_retention
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "009_release_evidence"
down_revision: str | None = "007_soft_delete_and_retention"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "release_evidence",
        sa.Column("run_id", sa.String(64), primary_key=True),
        sa.Column("teacher_id_hash", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("event_sequence", sa.JSON, nullable=True),
        sa.Column("artifact_ids", sa.JSON, nullable=True),
        sa.Column("snapshot_ids", sa.JSON, nullable=True),
        sa.Column("export_files", sa.JSON, nullable=True),
        sa.Column("trace_ids", sa.JSON, nullable=True),
        sa.Column("total_duration_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("per_stage_duration_ms", sa.JSON, nullable=True),
        sa.Column("tokens_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_release_evidence_status",
        "release_evidence",
        ["status"],
        schema="public",
    )
    op.create_index(
        "ix_release_evidence_created_at",
        "release_evidence",
        ["created_at"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_release_evidence_created_at", schema="public")
    op.drop_index("ix_release_evidence_status", schema="public")
    op.drop_table("release_evidence", schema="public")
