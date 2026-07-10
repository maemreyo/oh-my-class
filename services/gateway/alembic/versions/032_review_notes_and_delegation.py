"""Add anchored review notes and run-level reviewer delegation.

Revision ID: 032_review_notes_and_delegation
Revises: 031_teaching_briefs
Create Date: 2026-07-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "032_review_notes_and_delegation"
down_revision: str | None = "031_teaching_briefs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("artifact_review_notes", schema="public"):
        _create_review_notes()
    if not inspector.has_table("run_delegations", schema="public"):
        _create_run_delegations()


def _create_review_notes() -> None:
    op.create_table(
        "artifact_review_notes",
        sa.Column("note_id", sa.String(80), primary_key=True),
        sa.Column("run_id", sa.String(64), sa.ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_id", sa.String(80), nullable=False),
        sa.Column(
            "document_id",
            sa.String(80),
            sa.ForeignKey("public.artifact_documents.document_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content_entity_id", sa.String(80), nullable=True),
        sa.Column("author_id", sa.String(64), nullable=False),
        sa.Column("body", sa.String(2_000), nullable=False),
        sa.Column("blocking", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.create_index("ix_artifact_review_notes_document", "artifact_review_notes", ["document_id"], schema="public")


def _create_run_delegations() -> None:
    op.create_table(
        "run_delegations",
        sa.Column("delegation_id", sa.String(80), primary_key=True),
        sa.Column("run_id", sa.String(64), sa.ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("delegate_id", sa.String(64), nullable=False),
        sa.Column("granted_by", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("run_id", "delegate_id", name="uq_run_delegations_run_delegate"),
        schema="public",
    )
    op.create_index("ix_run_delegations_run", "run_delegations", ["run_id"], schema="public")


def downgrade() -> None:
    op.drop_index("ix_run_delegations_run", table_name="run_delegations", schema="public")
    op.drop_table("run_delegations", schema="public")
    op.drop_index("ix_artifact_review_notes_document", table_name="artifact_review_notes", schema="public")
    op.drop_table("artifact_review_notes", schema="public")
