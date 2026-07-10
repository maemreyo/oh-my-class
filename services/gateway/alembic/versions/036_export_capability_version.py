"""Add capability_version pin to export_records.

Revision ID: 036_export_capability_version
Revises: 035_media_asset_versions
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "036_export_capability_version"
down_revision: str | None = "035_media_asset_versions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("export_records", schema="public")}
    if "capability_version" not in columns:
        op.add_column(
            "export_records",
            sa.Column("capability_version", sa.String(32), nullable=True),
            schema="public",
        )


def downgrade() -> None:
    op.drop_column("export_records", "capability_version", schema="public")
