"""Add decomposition memory tables.

Revision ID: 017_decomposition_memory
Revises: 016_class_profiles
Create Date: 2026-07-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "017_decomposition_memory"
down_revision: str | None = "016_class_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "decomposition_feedback",
        sa.Column("feedback_id", sa.String(64), primary_key=True),
        sa.Column("teacher_id", sa.String(64), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("proposed_sequence", sa.JSON(), nullable=False),
        sa.Column("approved_sequence", sa.JSON(), nullable=False),
        sa.Column("edit_types", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema="public",
    )
    op.create_index("ix_decomposition_feedback_teacher_id", "decomposition_feedback", ["teacher_id"], schema="public")
    op.create_table(
        "decomposition_templates",
        sa.Column("template_id", sa.String(64), primary_key=True),
        sa.Column("teacher_id", sa.String(64), nullable=False),
        sa.Column("topic_normalized", sa.String(200), nullable=False),
        sa.Column("grade", sa.String(64), nullable=False),
        sa.Column("subject", sa.String(80), nullable=False),
        sa.Column("locale", sa.String(16), nullable=False),
        sa.Column("approved_sequence", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("teacher_id", "topic_normalized", "grade", "subject", "locale", name="uq_decomposition_template_key"),
        schema="public",
    )
    op.create_table(
        "teacher_decomposition_preferences",
        sa.Column("teacher_id", sa.String(64), primary_key=True),
        sa.Column("preferences", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("teacher_id", name="uq_teacher_decomposition_preferences_teacher"),
        schema="public",
    )


def downgrade() -> None:
    op.drop_table("teacher_decomposition_preferences", schema="public")
    op.drop_table("decomposition_templates", schema="public")
    op.drop_index("ix_decomposition_feedback_teacher_id", table_name="decomposition_feedback", schema="public")
    op.drop_table("decomposition_feedback", schema="public")
