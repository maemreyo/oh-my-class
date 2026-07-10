"""Add Source Collections, entries, and claim-to-evidence mappings.

Revision ID: 033_sources_claim_evidence
Revises: 032_review_notes_and_delegation
Create Date: 2026-07-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "033_sources_claim_evidence"
down_revision: str | None = "032_review_notes_and_delegation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("source_collections", schema="public"):
        _create_source_collections()
    if not inspector.has_table("source_collection_entries", schema="public"):
        _create_source_collection_entries()
    if not inspector.has_table("claim_evidence", schema="public"):
        _create_claim_evidence()


def _create_source_collections() -> None:
    op.create_table(
        "source_collections",
        sa.Column("collection_id", sa.String(80), primary_key=True),
        sa.Column("scope", sa.String(24), nullable=False),
        sa.Column("owner_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )


def _create_source_collection_entries() -> None:
    op.create_table(
        "source_collection_entries",
        sa.Column("entry_id", sa.String(80), primary_key=True),
        sa.Column(
            "collection_id",
            sa.String(80),
            sa.ForeignKey("public.source_collections.collection_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("authority", sa.String(16), nullable=False),
        sa.Column("url", sa.String(2_000), nullable=True),
        sa.Column("excerpt", sa.String(8_000), nullable=True),
        sa.Column("subject_key", sa.String(120), nullable=True),
        sa.Column("claim_value", sa.String(500), nullable=True),
        sa.Column("copyright_ack", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index(
        "ix_source_collection_entries_collection", "source_collection_entries", ["collection_id"], schema="public",
    )


def _create_claim_evidence() -> None:
    op.create_table(
        "claim_evidence",
        sa.Column("claim_evidence_id", sa.String(80), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(80),
            sa.ForeignKey("public.artifact_documents.document_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("claim_id", sa.String(80), nullable=False),
        sa.Column("claim_text", sa.String(2_000), nullable=False),
        sa.Column("risk_level", sa.String(16), nullable=False),
        sa.Column("verification_status", sa.String(16), nullable=False),
        sa.Column("citation_ids_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_claim_evidence_document", "claim_evidence", ["document_id"], schema="public")


def downgrade() -> None:
    op.drop_index("ix_claim_evidence_document", table_name="claim_evidence", schema="public")
    op.drop_table("claim_evidence", schema="public")
    op.drop_index(
        "ix_source_collection_entries_collection", table_name="source_collection_entries", schema="public",
    )
    op.drop_table("source_collection_entries", schema="public")
    op.drop_table("source_collections", schema="public")
