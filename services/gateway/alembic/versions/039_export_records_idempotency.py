"""#123 (OPS-10): exactly-once export_records -- unique (snapshot_id, format).

Revision ID: 039_export_records_idempotency
Revises: 038_run_job_dead_letter
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "039_export_records_idempotency"
down_revision: str | None = "038_run_job_dead_letter"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINT_NAME = "uq_export_records_snapshot_format"


def upgrade() -> None:
    bind = op.get_bind()
    # Pre-existing duplicate (snapshot_id, format) rows predate this
    # constraint (created before exactly-once enforcement existed) -- keep
    # the earliest row per group, drop the rest, so the constraint can be
    # added in any environment without a manual cleanup step first.
    bind.execute(sa.text("""
        DELETE FROM public.export_records er
        USING public.export_records newer
        WHERE er.snapshot_id = newer.snapshot_id
          AND er.format = newer.format
          AND (er.created_at, er.export_id) > (newer.created_at, newer.export_id)
    """))
    inspector = sa.inspect(bind)
    constraints = {c["name"] for c in inspector.get_unique_constraints("export_records", schema="public")}
    if _CONSTRAINT_NAME not in constraints:
        op.create_unique_constraint(
            _CONSTRAINT_NAME, "export_records", ["snapshot_id", "format"], schema="public",
        )


def downgrade() -> None:
    op.drop_constraint(_CONSTRAINT_NAME, "export_records", schema="public", type_="unique")
