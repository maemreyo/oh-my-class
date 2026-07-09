"""Add media_assets table for the teacher-scoped media library (SDX-02).

Revision ID: 023_media_assets
Revises: 022_teaching_session_join
Create Date: 2026-07-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "023_media_assets"
down_revision: str | None = "022_teaching_session_join"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("asset_id", sa.String(64), primary_key=True),
        sa.Column("teacher_id", sa.String(64), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("alt_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
        ),
        schema="public",
    )
    op.create_index(
        "ix_media_assets_teacher_id",
        "media_assets",
        ["teacher_id"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_media_assets_teacher_id", table_name="media_assets", schema="public")
    op.drop_table("media_assets", schema="public")
