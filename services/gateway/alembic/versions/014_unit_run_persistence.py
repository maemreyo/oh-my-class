"""Add unit parent/session persistence columns to runs.

Revision ID: 014_unit_run_persistence
Revises: 013_gate_active_unique
Create Date: 2026-06-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
import alembic.op as op

revision: str = "014_unit_run_persistence"
down_revision: str | None = "013_gate_active_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column("parent_run_id", sa.String(64), nullable=True),
        schema="public",
    )
    op.add_column(
        "runs",
        sa.Column("session_id", sa.String(64), nullable=True),
        schema="public",
    )
    op.add_column(
        "runs",
        sa.Column("session_index", sa.Integer(), nullable=True),
        schema="public",
    )
    op.add_column(
        "runs",
        sa.Column(
            "unit_role",
            sa.Enum("standalone", "unit_parent", "unit_session", name="unitrole", native_enum=False),
            nullable=False,
            server_default="standalone",
        ),
        schema="public",
    )
    op.add_column(
        "runs",
        sa.Column("lesson_sequence", sa.JSON(), nullable=True),
        schema="public",
    )
    op.add_column(
        "runs",
        sa.Column("shared_research", sa.JSON(), nullable=True),
        schema="public",
    )
    op.add_column(
        "runs",
        sa.Column("persona_snapshot", sa.JSON(), nullable=True),
        schema="public",
    )
    op.create_foreign_key(
        "fk_runs_parent_run_id",
        "runs",
        "runs",
        ["parent_run_id"],
        ["run_id"],
        source_schema="public",
        referent_schema="public",
        ondelete="CASCADE",
    )
    op.create_index("ix_runs_parent_run_id", "runs", ["parent_run_id"], schema="public")
    op.create_unique_constraint(
        "uq_runs_parent_session",
        "runs",
        ["parent_run_id", "session_id"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_constraint("uq_runs_parent_session", "runs", schema="public", type_="unique")
    op.drop_index("ix_runs_parent_run_id", table_name="runs", schema="public")
    op.drop_constraint("fk_runs_parent_run_id", "runs", schema="public", type_="foreignkey")
    op.drop_column("runs", "persona_snapshot", schema="public")
    op.drop_column("runs", "shared_research", schema="public")
    op.drop_column("runs", "lesson_sequence", schema="public")
    op.drop_column("runs", "unit_role", schema="public")
    op.drop_column("runs", "session_index", schema="public")
    op.drop_column("runs", "session_id", schema="public")
    op.drop_column("runs", "parent_run_id", schema="public")
