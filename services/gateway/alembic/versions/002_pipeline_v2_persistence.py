"""Pipeline V2 persistence tables.

Revision ID: 002_pipeline_v2_persistence
Revises: 001_initial
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002_pipeline_v2_persistence"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "run_status_history",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(64), sa.ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("stage", sa.String(64), nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index(
        "ix_run_status_history_run_id",
        "run_status_history",
        ["run_id"],
        schema="public",
    )

    op.create_table(
        "run_events",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(64), sa.ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.BigInteger, nullable=False),
        sa.Column("event_name", sa.String(128), nullable=False),
        sa.Column("stage", sa.String(64), nullable=True),
        sa.Column("visibility", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("run_id", "sequence", name="uq_run_events_run_sequence"),
        schema="public",
    )
    op.create_index(
        "ix_run_events_run_id_sequence",
        "run_events",
        ["run_id", "sequence"],
        schema="public",
    )
    op.create_index(
        "ix_run_events_run_id_visibility",
        "run_events",
        ["run_id", "visibility"],
        schema="public",
    )

    op.create_table(
        "artifact_snapshots",
        sa.Column("snapshot_id", sa.String(64), primary_key=True),
        sa.Column("run_id", sa.String(64), sa.ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_id", sa.String(64), nullable=False),
        sa.Column("artifact_type", sa.String(32), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("content_json", sa.JSON, nullable=True),
        sa.Column("rendered_html", sa.Text, nullable=False),
        sa.Column("renderer_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("content_hash", name="uq_artifact_snapshots_content_hash"),
        schema="public",
    )
    op.create_index(
        "ix_artifact_snapshots_run_id",
        "artifact_snapshots",
        ["run_id"],
        schema="public",
    )
    op.create_index(
        "ix_artifact_snapshots_artifact_id",
        "artifact_snapshots",
        ["artifact_id"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_artifact_snapshots_artifact_id", table_name="artifact_snapshots", schema="public")
    op.drop_index("ix_artifact_snapshots_run_id", table_name="artifact_snapshots", schema="public")
    op.drop_table("artifact_snapshots", schema="public")

    op.drop_index("ix_run_events_run_id_visibility", table_name="run_events", schema="public")
    op.drop_index("ix_run_events_run_id_sequence", table_name="run_events", schema="public")
    op.drop_table("run_events", schema="public")

    op.drop_index("ix_run_status_history_run_id", table_name="run_status_history", schema="public")
    op.drop_table("run_status_history", schema="public")
