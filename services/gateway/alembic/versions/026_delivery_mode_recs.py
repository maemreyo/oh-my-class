"""Add teaching_sessions.delivery_mode and session_recommendations (TSP-07).

`delivery_mode` is declared for all five modes now (live/homework/review/
flipped/catch_up) so adding the four async modes' runtime later is not a
breaking schema change -- only `live` is selectable today (see
`teaching_session.service.create_session`'s fail-closed gate).
`session_recommendations` holds teacher-approval-gated post-lesson
recommendation candidates (see `teaching_session/recommendations.py`) --
never auto-generated from.

Revision ID: 026_delivery_mode_recs
Revises: 025_teaching_session_events
Create Date: 2026-07-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "026_delivery_mode_recs"
down_revision: str | None = "025_teaching_session_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "teaching_sessions",
        sa.Column("delivery_mode", sa.String(16), nullable=False, server_default="live"),
        schema="public",
    )

    op.create_table(
        "session_recommendations",
        sa.Column("recommendation_id", sa.String(64), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("evidence_keys", sa.JSON(), nullable=False),
        sa.Column("rationale", sa.String(500), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(64), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_session_recommendations_session_id",
        "session_recommendations",
        ["session_id"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_session_recommendations_session_id",
        table_name="session_recommendations",
        schema="public",
    )
    op.drop_table("session_recommendations", schema="public")
    op.drop_column("teaching_sessions", "delivery_mode", schema="public")
