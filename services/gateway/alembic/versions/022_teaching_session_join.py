"""Add teaching_sessions.room_code and class_roster_entries (TSP-02).

`room_code` is the anonymous-first join affordance (QR-primary, 6-digit
numeric fallback) -- nullable, no DB-level uniqueness constraint by design
(see `teaching_session/service.py::_unique_room_code`'s ponytail note: join
lookups already scope to non-terminal sessions, so a stale ended session's
code can be safely reused without a partial-unique index in this slice).
`class_roster_entries` backs the CSV roster import for identifiable-tier
name-select joins (amendment #4) -- no relation to `users`.

Revision ID: 022_teaching_session_join
Revises: 021_teaching_sessions
Create Date: 2026-07-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "022_teaching_session_join"
down_revision: str | None = "021_teaching_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "teaching_sessions",
        sa.Column("room_code", sa.String(6), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_teaching_sessions_room_code", "teaching_sessions", ["room_code"], schema="public",
    )

    op.create_table(
        "class_roster_entries",
        sa.Column("roster_entry_id", sa.String(64), primary_key=True),
        sa.Column("class_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("student_id", sa.String(64), nullable=True),
        sa.Column("imported_by", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema="public",
    )
    op.create_index(
        "ix_class_roster_entries_class_id", "class_roster_entries", ["class_id"], schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_class_roster_entries_class_id", table_name="class_roster_entries", schema="public",
    )
    op.drop_table("class_roster_entries", schema="public")

    op.drop_index("ix_teaching_sessions_room_code", table_name="teaching_sessions", schema="public")
    op.drop_column("teaching_sessions", "room_code", schema="public")
