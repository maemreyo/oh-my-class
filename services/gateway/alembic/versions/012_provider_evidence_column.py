"""Add provider_evidence column to release_evidence table.

Revision ID: 012_provider_evidence_column
Revises: 011_queued_job_eligible_at
Create Date: 2026-06-28

Adds the ``provider_evidence`` nullable JSON column to
``public.release_evidence``.  The ORM model
(``ReleaseEvidenceRecord.provider_evidence``) already declares this column,
but migration 009 did not include it — causing schema drift on
migration-managed deployments.

Downgrade cleanly removes the column.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "012_provider_evidence_column"
down_revision: str | None = "011_queued_job_eligible_at"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "release_evidence",
        sa.Column("provider_evidence", sa.JSON, nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("release_evidence", "provider_evidence", schema="public")
