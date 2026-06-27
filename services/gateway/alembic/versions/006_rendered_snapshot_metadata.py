"""Rendered snapshot metadata.

Revision ID: 006_rendered_snapshot_metadata
Revises: 005_artifact_workflow_state
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006_rendered_snapshot_metadata"
down_revision: str | None = "005_artifact_workflow_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.add_column(
        "artifact_snapshots",
        sa.Column("html_hash", sa.String(64), nullable=False, server_default=""),
        schema="public",
    )
    op.add_column(
        "artifact_snapshots",
        sa.Column("student_rendered_html", sa.Text, nullable=False, server_default=""),
        schema="public",
    )
    op.add_column(
        "artifact_snapshots",
        sa.Column("template_version", sa.String(64), nullable=False, server_default="unknown"),
        schema="public",
    )
    op.add_column(
        "artifact_snapshots",
        sa.Column("theme_version", sa.String(64), nullable=False, server_default="unknown"),
        schema="public",
    )
    op.add_column(
        "artifact_snapshots",
        sa.Column("standalone_valid", sa.Boolean, nullable=False, server_default=sa.false()),
        schema="public",
    )
    op.add_column(
        "artifact_snapshots",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.execute(
        """
        UPDATE public.artifact_snapshots
        SET html_hash = encode(digest(rendered_html, 'sha256'), 'hex')
        WHERE html_hash = ''
        """,
    )
    op.execute(
        """
        UPDATE public.artifact_snapshots
        SET student_rendered_html =
            '<!DOCTYPE html><html><body><section>' ||
            'oh-my-class legacy preview unavailable' ||
            '</section></body></html>'
        WHERE student_rendered_html = ''
        """,
    )
    op.execute(
        """
        UPDATE public.artifact_snapshots
        SET standalone_valid = true
        WHERE lower(rendered_html) LIKE '%<!doctype html%'
          AND lower(rendered_html) NOT LIKE '%http://%'
          AND lower(rendered_html) NOT LIKE '%https://%'
          AND lower(rendered_html) NOT LIKE '%<link%'
          AND lower(rendered_html) NOT LIKE '%<script src=%'
        """,
    )


def downgrade() -> None:
    op.drop_column("artifact_snapshots", "approved_at", schema="public")
    op.drop_column("artifact_snapshots", "standalone_valid", schema="public")
    op.drop_column("artifact_snapshots", "theme_version", schema="public")
    op.drop_column("artifact_snapshots", "template_version", schema="public")
    op.drop_column("artifact_snapshots", "student_rendered_html", schema="public")
    op.drop_column("artifact_snapshots", "html_hash", schema="public")
