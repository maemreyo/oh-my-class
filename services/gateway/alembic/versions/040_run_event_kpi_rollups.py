"""#120 (OPS-07): daily KPI rollup table for run_events pruning.

Additive-only -- creates `run_event_kpi_rollups` alongside the existing
`run_events` table. No existing table is touched (expand-first, OPS-08).

Revision ID: 040_run_event_kpi_rollups
Revises: 039_export_records_idempotency
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "040_run_event_kpi_rollups"
down_revision: str | None = "039_export_records_idempotency"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "run_event_kpi_rollups",
        sa.Column("day", sa.Date(), primary_key=True, nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fail_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("escalate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("breaker_trip_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("healing_distribution", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("run_latency_p95_seconds", sa.Float(), nullable=True),
        sa.Column(
            "computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
        ),
        schema="public",
    )


def downgrade() -> None:
    op.drop_table("run_event_kpi_rollups", schema="public")
