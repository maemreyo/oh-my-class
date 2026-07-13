"""#471/#472: transactional run-event outbox and mandatory run organization.

Revision ID: 041_run_event_outbox_and_tenant_scope
Revises: 040_run_event_kpi_rollups
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "041_run_event_outbox_and_tenant_scope"
down_revision: str | None = "040_run_event_kpi_rollups"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("organization_id", sa.String(length=80), nullable=True), schema="public")
    op.execute("UPDATE public.runs SET organization_id = 'teacher:' || teacher_id WHERE organization_id IS NULL")
    op.alter_column("runs", "organization_id", existing_type=sa.String(length=80), nullable=False, schema="public")
    op.create_index("ix_runs_organization_id", "runs", ["organization_id"], schema="public")

    op.create_table(
        "run_event_outbox",
        sa.Column("outbox_id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column(
            "run_id",
            sa.String(length=64),
            sa.ForeignKey("public.runs.run_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_owner", sa.String(length=128), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("dedupe_key", name="uq_run_event_outbox_dedupe_key"),
        sa.UniqueConstraint("run_id", "sequence", name="uq_run_event_outbox_run_sequence"),
        schema="public",
    )
    op.create_index(
        "ix_run_event_outbox_claim",
        "run_event_outbox",
        ["status", "available_at", "lease_expires_at"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_run_event_outbox_claim", table_name="run_event_outbox", schema="public")
    op.drop_table("run_event_outbox", schema="public")
    op.drop_index("ix_runs_organization_id", table_name="runs", schema="public")
    op.drop_column("runs", "organization_id", schema="public")
