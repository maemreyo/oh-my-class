"""Add session_student_responses and session_response_aggregates (TSP-05).

Raw per-student response capture (only ever populated for pseudonymous/
identifiable retention tiers) and the always-on class-concept/misconception
aggregate counters the default analytics read (`teaching_session.responses`).

Revision ID: 024_session_responses
Revises: 023_media_assets
Create Date: 2026-07-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "024_session_responses"
down_revision: str | None = "023_media_assets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "session_student_responses",
        sa.Column("response_id", sa.String(64), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("interaction_id", sa.String(80), nullable=False),
        sa.Column("student_pseudonym", sa.String(128), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("kc_ids", sa.JSON(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema="public",
    )
    op.create_index(
        "ix_session_student_responses_session_id",
        "session_student_responses",
        ["session_id"],
        schema="public",
    )
    op.create_index(
        "ix_session_student_responses_student_pseudonym",
        "session_student_responses",
        ["student_pseudonym"],
        schema="public",
    )

    op.create_table(
        "session_response_aggregates",
        sa.Column("aggregate_id", sa.String(64), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("interaction_id", sa.String(80), nullable=False),
        sa.Column("kc_ids", sa.JSON(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "session_id", "interaction_id",
            name="uq_session_response_aggregates_session_interaction",
        ),
        schema="public",
    )
    op.create_index(
        "ix_session_response_aggregates_session_id",
        "session_response_aggregates",
        ["session_id"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_session_response_aggregates_session_id",
        table_name="session_response_aggregates",
        schema="public",
    )
    op.drop_table("session_response_aggregates", schema="public")

    op.drop_index(
        "ix_session_student_responses_student_pseudonym",
        table_name="session_student_responses",
        schema="public",
    )
    op.drop_index(
        "ix_session_student_responses_session_id",
        table_name="session_student_responses",
        schema="public",
    )
    op.drop_table("session_student_responses", schema="public")
