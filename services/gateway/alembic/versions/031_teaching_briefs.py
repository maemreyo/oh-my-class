"""Add durable teacher-owned Teaching Brief drafts.

Revision ID: 031_teaching_briefs
Revises: 030_artifact_document_lineage
Create Date: 2026-07-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "031_teaching_briefs"
down_revision: str | None = "030_artifact_document_lineage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("teaching_briefs", schema="public"):
        return
    op.create_table(
        "teaching_briefs",
        sa.Column("brief_id", sa.String(64), primary_key=True),
        sa.Column("teacher_id", sa.String(64), nullable=False),
        sa.Column("brief_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_teaching_briefs_teacher_id", "teaching_briefs", ["teacher_id"], schema="public")


def downgrade() -> None:
    op.drop_index("ix_teaching_briefs_teacher_id", table_name="teaching_briefs", schema="public")
    op.drop_table("teaching_briefs", schema="public")
