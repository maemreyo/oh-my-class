"""Add export_records for versioned exports and staleness tracking (SDE-06).

Every exported file gets one row pinned to the snapshot_id it was generated
from. Rows are append-only (no update/delete path) so older exports remain
reachable after later edits create new snapshots. Staleness is a read-time
comparison between an artifact's latest export_records row and its current
head snapshot (see teaching_pack_export_store.py).

Revision ID: 027_export_records
Revises: 026_delivery_mode_recs
Create Date: 2026-07-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "027_export_records"
down_revision: str | None = "026_delivery_mode_recs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "export_records",
        sa.Column("export_id", sa.String(64), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(64),
            sa.ForeignKey("public.runs.run_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("artifact_id", sa.String(64), nullable=False),
        sa.Column(
            "snapshot_id",
            sa.String(64),
            sa.ForeignKey("public.artifact_snapshots.snapshot_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("format", sa.String(32), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema="public",
    )
    op.create_index(
        "ix_export_records_run_id", "export_records", ["run_id"], schema="public",
    )
    op.create_index(
        "ix_export_records_artifact_id", "export_records", ["artifact_id"], schema="public",
    )
    op.create_index(
        "ix_export_records_snapshot_id", "export_records", ["snapshot_id"], schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_export_records_snapshot_id", table_name="export_records", schema="public")
    op.drop_index("ix_export_records_artifact_id", table_name="export_records", schema="public")
    op.drop_index("ix_export_records_run_id", table_name="export_records", schema="public")
    op.drop_table("export_records", schema="public")
