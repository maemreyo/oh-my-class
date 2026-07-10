"""Add immutable Media Asset versions, dependencies, and Visual Source Suggestions.

Revision ID: 035_media_asset_versions
Revises: 034_content_briefs
Create Date: 2026-07-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "035_media_asset_versions"
down_revision: str | None = "034_content_briefs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("media_asset_versions", schema="public"):
        _create_media_asset_versions()
    if not inspector.has_table("media_asset_dependencies", schema="public"):
        _create_media_asset_dependencies()
    if not inspector.has_table("visual_source_suggestions", schema="public"):
        _create_visual_source_suggestions()


def _create_media_asset_versions() -> None:
    op.create_table(
        "media_asset_versions",
        sa.Column("version_id", sa.String(80), primary_key=True),
        sa.Column("asset_id", sa.String(80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("owner_scope", sa.String(24), nullable=False),
        sa.Column("owner_id", sa.String(64), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("license_note", sa.String(500), nullable=True),
        sa.Column("alt_text", sa.String(500), nullable=True),
        sa.Column(
            "parent_version_id",
            sa.String(80),
            sa.ForeignKey("public.media_asset_versions.version_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_media_asset_versions_asset", "media_asset_versions", ["asset_id"], schema="public")


def _create_media_asset_dependencies() -> None:
    op.create_table(
        "media_asset_dependencies",
        sa.Column("dependency_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "media_version_id",
            sa.String(80),
            sa.ForeignKey("public.media_asset_versions.version_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.String(80),
            sa.ForeignKey("public.artifact_documents.document_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index(
        "ix_media_asset_dependencies_version", "media_asset_dependencies", ["media_version_id"], schema="public",
    )
    op.create_index(
        "ix_media_asset_dependencies_document", "media_asset_dependencies", ["document_id"], schema="public",
    )


def _create_visual_source_suggestions() -> None:
    op.create_table(
        "visual_source_suggestions",
        sa.Column("suggestion_id", sa.String(80), primary_key=True),
        sa.Column("run_id", sa.String(64), sa.ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("description", sa.String(1_000), nullable=False),
        sa.Column("candidate_url", sa.String(2_000), nullable=True),
        sa.Column("license_hint", sa.String(500), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("converted_asset_id", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index(
        "ix_visual_source_suggestions_run", "visual_source_suggestions", ["run_id"], schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_visual_source_suggestions_run", table_name="visual_source_suggestions", schema="public")
    op.drop_table("visual_source_suggestions", schema="public")
    op.drop_index(
        "ix_media_asset_dependencies_document", table_name="media_asset_dependencies", schema="public",
    )
    op.drop_index(
        "ix_media_asset_dependencies_version", table_name="media_asset_dependencies", schema="public",
    )
    op.drop_table("media_asset_dependencies", schema="public")
    op.drop_index("ix_media_asset_versions_asset", table_name="media_asset_versions", schema="public")
    op.drop_table("media_asset_versions", schema="public")
