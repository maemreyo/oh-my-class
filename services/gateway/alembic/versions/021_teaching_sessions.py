"""Add teaching_sessions and teaching_session_audit_events (TSP-01).

TeachingSession is a privacy-first overlay on an immutable slide-deck
snapshot (ADR-046). `teaching_session_audit_events` is a minimal, session-
scoped audit trail seeded now for the identifiable-tier acknowledgment
requirement (TSP-01 amendment #3), shaped so a future PRIV-01 data-access log
can absorb it.

Revision ID: 021_teaching_sessions
Revises: 020_fix_delivery_fk_deferrable
Create Date: 2026-07-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "021_teaching_sessions"
down_revision: str | None = "020_fix_delivery_fk_deferrable"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "teaching_sessions",
        sa.Column("session_id", sa.String(64), primary_key=True),
        sa.Column("teacher_id", sa.String(64), nullable=False),
        sa.Column("class_id", sa.String(64), nullable=True),
        sa.Column("deck_id", sa.String(80), nullable=False),
        sa.Column("snapshot_id", sa.String(80), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="scheduled"),
        sa.Column("retention_tier", sa.String(32), nullable=False, server_default="aggregate"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_teaching_sessions_teacher_id", "teaching_sessions", ["teacher_id"], schema="public",
    )
    op.create_index(
        "ix_teaching_sessions_class_id", "teaching_sessions", ["class_id"], schema="public",
    )
    op.create_index(
        "ix_teaching_sessions_deck_id", "teaching_sessions", ["deck_id"], schema="public",
    )

    op.create_table(
        "teaching_session_audit_events",
        sa.Column("event_id", sa.String(64), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(64),
            sa.ForeignKey("public.teaching_sessions.session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actor_id", sa.String(64), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("event_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema="public",
    )
    op.create_index(
        "ix_teaching_session_audit_events_session_id",
        "teaching_session_audit_events",
        ["session_id"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_teaching_session_audit_events_session_id",
        table_name="teaching_session_audit_events",
        schema="public",
    )
    op.drop_table("teaching_session_audit_events", schema="public")

    op.drop_index("ix_teaching_sessions_deck_id", table_name="teaching_sessions", schema="public")
    op.drop_index("ix_teaching_sessions_class_id", table_name="teaching_sessions", schema="public")
    op.drop_index(
        "ix_teaching_sessions_teacher_id", table_name="teaching_sessions", schema="public",
    )
    op.drop_table("teaching_sessions", schema="public")
