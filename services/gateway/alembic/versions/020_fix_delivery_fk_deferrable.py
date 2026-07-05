"""Make delivery_records.run_id FK deferrable to prevent deadlock.

The FK fk_delivery_records_run_id caused an application-level deadlock:
  - Main job session holds an uncommitted UPDATE on runs (status transitions)
  - A concurrent record_post_export_delivery session INSERTs into delivery_records
  - PostgreSQL's immediate FK check waits for the runs row lock to clear
  - But the main session won't commit until Python awaits the delivery INSERT
  → circular wait that PostgreSQL's deadlock detector cannot see

Fix: make the FK DEFERRABLE INITIALLY DEFERRED so the constraint is checked
at COMMIT time rather than at statement time. By commit time the runs row is
either already committed by the main session, or the delivery session commits
independently — either way no lock contention.

Revision ID: 020_fix_delivery_fk_deferrable
Revises: 019_vocabulary_cluster_workflows
Create Date: 2026-07-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "020_fix_delivery_fk_deferrable"
down_revision: str | None = "019_vocabulary_cluster_workflows"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "fk_delivery_records_run_id",
        "delivery_records",
        schema="public",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_delivery_records_run_id",
        "delivery_records",
        "runs",
        ["run_id"],
        ["run_id"],
        source_schema="public",
        referent_schema="public",
        ondelete="CASCADE",
        deferrable=True,
        initially="DEFERRED",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_delivery_records_run_id",
        "delivery_records",
        schema="public",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_delivery_records_run_id",
        "delivery_records",
        "runs",
        ["run_id"],
        ["run_id"],
        source_schema="public",
        referent_schema="public",
        ondelete="CASCADE",
    )
