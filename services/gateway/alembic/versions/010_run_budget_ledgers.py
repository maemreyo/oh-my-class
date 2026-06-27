"""Create run_budget_ledgers table.

Revision ID: 010_run_budget_ledgers
Revises: 009_release_evidence
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "010_run_budget_ledgers"
down_revision: str | None = "009_release_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "run_budget_ledgers",
        sa.Column("run_id", sa.String(64), primary_key=True),
        sa.Column("tokens_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("searches_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("fetches_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("retries_used", sa.JSON, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_table("run_budget_ledgers", schema="public")
