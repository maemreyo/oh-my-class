"""Add Content Briefs and the append-only strategy review path.

Revision ID: 034_content_briefs
Revises: 033_sources_claim_evidence
Create Date: 2026-07-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "034_content_briefs"
down_revision: str | None = "033_sources_claim_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("content_briefs", schema="public"):
        _create_content_briefs()
    if not inspector.has_table("strategy_review_requests", schema="public"):
        _create_strategy_review_requests()


def _create_content_briefs() -> None:
    op.create_table(
        "content_briefs",
        sa.Column("content_brief_id", sa.String(80), primary_key=True),
        sa.Column("run_id", sa.String(64), sa.ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_type", sa.String(32), nullable=False),
        sa.Column("brief_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_content_briefs_run", "content_briefs", ["run_id"], schema="public")


def _create_strategy_review_requests() -> None:
    op.create_table(
        "strategy_review_requests",
        sa.Column("request_id", sa.String(80), primary_key=True),
        sa.Column(
            "content_brief_id",
            sa.String(80),
            sa.ForeignKey("public.content_briefs.content_brief_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_type", sa.String(24), nullable=False),
        sa.Column("reason_or_kind", sa.String(32), nullable=False),
        sa.Column("detail", sa.String(2_000), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_strategy_review_requests_brief", "strategy_review_requests", ["content_brief_id"], schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_strategy_review_requests_brief", table_name="strategy_review_requests", schema="public",
    )
    op.drop_table("strategy_review_requests", schema="public")
    op.drop_index("ix_content_briefs_run", table_name="content_briefs", schema="public")
    op.drop_table("content_briefs", schema="public")
