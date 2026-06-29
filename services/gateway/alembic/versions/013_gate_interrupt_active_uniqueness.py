"""Allow sequential responded gates with the same name.

Revision ID: 013_gate_active_unique
Revises: 012_provider_evidence_column
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "013_gate_active_unique"
down_revision: str | None = "012_provider_evidence_column"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_gate_interrupts_status",
        "gate_interrupts",
        schema="public",
        type_="unique",
    )
    op.create_index(
        "uq_gate_interrupts_active",
        "gate_interrupts",
        ["run_id", "gate_name"],
        unique=True,
        schema="public",
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_gate_interrupts_active",
        table_name="gate_interrupts",
        schema="public",
    )
    op.create_unique_constraint(
        "uq_gate_interrupts_status",
        "gate_interrupts",
        ["run_id", "gate_name", "status"],
        schema="public",
    )
