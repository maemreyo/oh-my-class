"""Add session_class_recaps for teacher-mediated class recap sharing (TSP-09).

Draft -> shared, mirroring `session_recommendations`' pending -> approved
shape. `share_token` is only ever set on share (an opaque, unauthenticated
lookup key -- see `teaching_session/recap.py`), never a parent login/account.

Revision ID: 028_session_class_recaps
Revises: 027_export_records
Create Date: 2026-07-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "028_session_class_recaps"
down_revision: str | None = "027_export_records"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "session_class_recaps",
        sa.Column("recap_id", sa.String(64), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("share_token", sa.String(64), nullable=True, unique=True),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("shared_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shared_by", sa.String(64), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_session_class_recaps_session_id",
        "session_class_recaps",
        ["session_id"],
        schema="public",
    )
    op.create_index(
        "ix_session_class_recaps_share_token",
        "session_class_recaps",
        ["share_token"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_session_class_recaps_share_token", table_name="session_class_recaps", schema="public",
    )
    op.drop_index(
        "ix_session_class_recaps_session_id", table_name="session_class_recaps", schema="public",
    )
    op.drop_table("session_class_recaps", schema="public")
