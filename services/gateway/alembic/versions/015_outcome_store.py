"""Create outcome store tables for effectiveness-loop subsystem.

Revision ID: 015_outcome_store
Revises: 014_unit_run_persistence
Create Date: 2026-06-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "015_outcome_store"
down_revision: str | None = "014_unit_run_persistence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # student_attempts
    op.create_table(
        "student_attempts",
        sa.Column("attempt_id", sa.String(64), primary_key=True),
        sa.Column("student_pseudonym", sa.String(128), nullable=False),
        sa.Column("question_id", sa.String(128), nullable=False),
        sa.Column("kc_ids", sa.JSON(), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivery_id", sa.String(64), nullable=False),
        sa.Column("teacher_id", sa.String(64), nullable=False),
        schema="public",
    )
    op.create_index(
        "ix_student_attempts_teacher_pseudonym",
        "student_attempts",
        ["teacher_id", "student_pseudonym"],
        schema="public",
    )

    # student_kc_states
    op.create_table(
        "student_kc_states",
        sa.Column("state_id", sa.String(64), primary_key=True),
        sa.Column("student_pseudonym", sa.String(128), nullable=False),
        sa.Column("kc_id", sa.String(64), nullable=False),
        sa.Column("mastery", sa.Float(), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("teacher_id", sa.String(64), nullable=False),
        sa.UniqueConstraint(
            "teacher_id", "student_pseudonym", "kc_id",
            name="uq_student_kc_states_teacher_pseudo_kc",
        ),
        schema="public",
    )

    # delivery_records
    op.create_table(
        "delivery_records",
        sa.Column("delivery_id", sa.String(64), primary_key=True),
        sa.Column("run_id", sa.String(64), nullable=False),
        sa.Column("teacher_id", sa.String(64), nullable=False),
        sa.Column("kc_ids", sa.JSON(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("class_id", sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["public.runs.run_id"],
            name="fk_delivery_records_run_id",
            ondelete="CASCADE",
        ),
        schema="public",
    )

    # guardian_consents
    op.create_table(
        "guardian_consents",
        sa.Column("consent_id", sa.String(64), primary_key=True),
        sa.Column("teacher_id", sa.String(64), nullable=False),
        sa.Column("class_id", sa.String(64), nullable=False),
        sa.Column("student_pseudonym", sa.String(128), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "teacher_id", "class_id", "student_pseudonym",
            name="uq_guardian_consents_active",
        ),
        schema="public",
    )


def downgrade() -> None:
    op.drop_table("guardian_consents", schema="public")
    op.drop_table("delivery_records", schema="public")
    op.drop_table("student_kc_states", schema="public")
    op.drop_index(
        "ix_student_attempts_teacher_pseudonym",
        table_name="student_attempts",
        schema="public",
    )
    op.drop_table("student_attempts", schema="public")
