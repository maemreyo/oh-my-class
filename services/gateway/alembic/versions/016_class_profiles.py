"""Add durable class profiles.

Revision ID: 016_class_profiles
Revises: 015_outcome_store
Create Date: 2026-07-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "016_class_profiles"
down_revision: str | None = "015_outcome_store"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "class_profiles",
        sa.Column("class_profile_id", sa.String(64), primary_key=True),
        sa.Column("teacher_id", sa.String(64), nullable=False),
        sa.Column("profile_json", sa.JSON(), nullable=False),
        sa.Column("schema_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retention_days", sa.Integer(), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_class_profiles_teacher_id",
        "class_profiles",
        ["teacher_id"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_class_profiles_teacher_id", table_name="class_profiles", schema="public")
    op.drop_table("class_profiles", schema="public")
