"""Add template_effectiveness table for RISE effectiveness loop.

Revision ID: 018_template_effectiveness
Revises: 017_decomposition_memory
Create Date: 2026-07-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "018_template_effectiveness"
down_revision: str | None = "017_decomposition_memory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "template_effectiveness",
        sa.Column("effectiveness_id", sa.String(64), primary_key=True),
        sa.Column("template_id", sa.String(64), nullable=False),
        sa.Column("topic_normalized", sa.String(200), nullable=False),
        sa.Column("grade", sa.String(64), nullable=False),
        sa.Column("subject", sa.String(80), nullable=False),
        sa.Column("locale", sa.String(16), nullable=False),
        sa.Column("methodology", sa.String(128), nullable=True),
        sa.Column("average_mastery_gain", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("template_id", name="uq_template_effectiveness_template_id"),
        schema="public",
    )
    op.create_index(
        "ix_template_effectiveness_topic_grade_subject_locale",
        "template_effectiveness",
        ["topic_normalized", "grade", "subject", "locale"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_template_effectiveness_topic_grade_subject_locale",
        table_name="template_effectiveness",
        schema="public",
    )
    op.drop_table("template_effectiveness", schema="public")
