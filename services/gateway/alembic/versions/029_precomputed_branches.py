"""Add precomputed_branches for live-session branching (TSP-06).

Quality-gated branch variants (reteach/hint/simpler_example/challenge/
extra_practice) attached to a deck/slide (+ optional interaction) -- see
`teaching_session/branches.py::create_precomputed_branch`, the sole insert
path (both hand-authored and AI-approved rows go through the same quality
gate before landing here).

Revision ID: 029_precomputed_branches
Revises: 028_session_class_recaps
Create Date: 2026-07-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "029_precomputed_branches"
down_revision: str | None = "028_session_class_recaps"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "precomputed_branches",
        sa.Column("branch_id", sa.String(64), primary_key=True),
        sa.Column("deck_id", sa.String(80), nullable=False),
        sa.Column("slide_id", sa.String(80), nullable=False),
        sa.Column("interaction_id", sa.String(80), nullable=True),
        sa.Column("branch_type", sa.String(24), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source", sa.String(16), nullable=False, server_default="precomputed"),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema="public",
    )
    op.create_index(
        "ix_precomputed_branches_deck_id_slide_id",
        "precomputed_branches",
        ["deck_id", "slide_id"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_precomputed_branches_deck_id_slide_id",
        table_name="precomputed_branches",
        schema="public",
    )
    op.drop_table("precomputed_branches", schema="public")
