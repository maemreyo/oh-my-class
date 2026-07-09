"""Add teaching_session_events append-only log (TSP-03).

Postgres write-behind for the Redis-hot `SessionReadModel` -- see
`teaching_session/event_log.py` and `teaching_session/live_sync.py`.
`sequence` is per-session monotonic (mirrors `run_events.sequence`'s shape
from `002_pipeline_v2_persistence.py`); `idempotency_key` is nullable so only
student-submission routes (which always pass one) participate in the unique
constraint -- Postgres treats NULLs as distinct, so every other event type is
unaffected.

Revision ID: 025_teaching_session_events
Revises: 024_session_responses
Create Date: 2026-07-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "025_teaching_session_events"
down_revision: str | None = "024_session_responses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "teaching_session_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "session_id",
            sa.String(64),
            sa.ForeignKey("public.teaching_sessions.session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("actor_role", sa.String(20), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "session_id", "sequence", name="uq_teaching_session_events_session_sequence",
        ),
        sa.UniqueConstraint(
            "session_id", "idempotency_key", name="uq_teaching_session_events_idempotency_key",
        ),
        schema="public",
    )
    op.create_index(
        "ix_teaching_session_events_session_id_sequence",
        "teaching_session_events",
        ["session_id", "sequence"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_teaching_session_events_session_id_sequence",
        table_name="teaching_session_events",
        schema="public",
    )
    op.drop_table("teaching_session_events", schema="public")
