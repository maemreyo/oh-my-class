"""Add append-only V2 artifact-document lineage tables.

Revision ID: 030_artifact_document_lineage
Revises: 029_precomputed_branches
Create Date: 2026-07-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "030_artifact_document_lineage"
down_revision: str | None = "029_precomputed_branches"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("artifact_documents", schema="public"):
        _create_artifact_documents()
    if not inspector.has_table("answer_sets", schema="public"):
        _create_answer_sets()
    if not inspector.has_table("content_variants", schema="public"):
        _create_content_variants()
    if not inspector.has_table("content_dependencies", schema="public"):
        _create_content_dependencies()
    if not inspector.has_table("content_approvals", schema="public"):
        _create_content_approvals()
    if not inspector.has_table("artifact_document_snapshots", schema="public"):
        _create_artifact_document_snapshots()


def _create_artifact_documents() -> None:
    op.create_table(
        "artifact_documents",
        sa.Column("document_id", sa.String(80), primary_key=True),
        sa.Column("run_id", sa.String(64), sa.ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_id", sa.String(80), nullable=False),
        sa.Column("artifact_type", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(8), nullable=False),
        sa.Column("audience", sa.String(16), nullable=False),
        sa.Column("authority", sa.String(32), nullable=False),
        sa.Column("parent_document_id", sa.String(80), sa.ForeignKey("public.artifact_documents.document_id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_document_id", sa.String(80), sa.ForeignKey("public.artifact_documents.document_id", ondelete="SET NULL"), nullable=True),
        sa.Column("document_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("run_id", "artifact_id", "version", name="uq_artifact_documents_version"),
        schema="public",
    )
    op.create_index("ix_artifact_documents_run_artifact", "artifact_documents", ["run_id", "artifact_id"], schema="public")


def _create_answer_sets() -> None:
    op.create_table(
        "answer_sets",
        sa.Column("answer_set_id", sa.String(80), primary_key=True),
        sa.Column("source_document_id", sa.String(80), sa.ForeignKey("public.artifact_documents.document_id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("authority", sa.String(32), nullable=False),
        sa.Column("answer_set_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source_document_id", "source_version", name="uq_answer_sets_document_version"),
        schema="public",
    )
    op.create_index("ix_answer_sets_source_document", "answer_sets", ["source_document_id"], schema="public")


def _create_content_variants() -> None:
    op.create_table(
        "content_variants",
        sa.Column("variant_id", sa.String(80), primary_key=True),
        sa.Column("document_id", sa.String(80), sa.ForeignKey("public.artifact_documents.document_id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_document_id", sa.String(80), sa.ForeignKey("public.artifact_documents.document_id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_kind", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("document_id", "variant_kind", name="uq_content_variants_document_kind"),
        schema="public",
    )
    op.create_index("ix_content_variants_source_document", "content_variants", ["source_document_id"], schema="public")


def _create_content_dependencies() -> None:
    op.create_table(
        "content_dependencies",
        sa.Column("dependency_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.String(80), sa.ForeignKey("public.artifact_documents.document_id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_document_id", sa.String(80), sa.ForeignKey("public.artifact_documents.document_id", ondelete="CASCADE"), nullable=False),
        sa.Column("dependency_kind", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("document_id", "source_document_id", "dependency_kind", name="uq_content_dependencies_edge"),
        schema="public",
    )
    op.create_index("ix_content_dependencies_source_document", "content_dependencies", ["source_document_id"], schema="public")


def _create_content_approvals() -> None:
    op.create_table(
        "content_approvals",
        sa.Column("approval_id", sa.String(80), primary_key=True),
        sa.Column("document_id", sa.String(80), sa.ForeignKey("public.artifact_documents.document_id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("approved_by", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_content_approvals_document", "content_approvals", ["document_id"], schema="public")


def _create_artifact_document_snapshots() -> None:
    op.create_table(
        "artifact_document_snapshots",
        sa.Column("document_id", sa.String(80), sa.ForeignKey("public.artifact_documents.document_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("snapshot_id", sa.String(64), sa.ForeignKey("public.artifact_snapshots.snapshot_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_artifact_document_snapshots_snapshot", "artifact_document_snapshots", ["snapshot_id"], schema="public")


def downgrade() -> None:
    op.drop_index("ix_artifact_document_snapshots_snapshot", table_name="artifact_document_snapshots", schema="public")
    op.drop_table("artifact_document_snapshots", schema="public")
    op.drop_index("ix_content_approvals_document", table_name="content_approvals", schema="public")
    op.drop_table("content_approvals", schema="public")
    op.drop_index("ix_content_dependencies_source_document", table_name="content_dependencies", schema="public")
    op.drop_table("content_dependencies", schema="public")
    op.drop_index("ix_content_variants_source_document", table_name="content_variants", schema="public")
    op.drop_table("content_variants", schema="public")
    op.drop_index("ix_answer_sets_source_document", table_name="answer_sets", schema="public")
    op.drop_table("answer_sets", schema="public")
    op.drop_index("ix_artifact_documents_run_artifact", table_name="artifact_documents", schema="public")
    op.drop_table("artifact_documents", schema="public")
