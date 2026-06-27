"""Pipeline V2 contract, gate, and artifact workflow tables.

Revision ID: 003_pipeline_v2_control_tables
Revises: 002_pipeline_v2_persistence
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003_pipeline_v2_control_tables"
down_revision: str | None = "002_pipeline_v2_persistence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "run_contracts",
        sa.Column("contract_id", sa.String(64), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(64),
            sa.ForeignKey("public.runs.run_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("teacher_id", sa.String(64), nullable=False),
        sa.Column("contract_json", sa.JSON, nullable=False),
        sa.Column("current_revision", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("run_id", name="uq_run_contracts_run_id"),
        schema="public",
    )
    op.create_table(
        "contract_revisions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "contract_id",
            sa.String(64),
            sa.ForeignKey("public.run_contracts.contract_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            sa.String(64),
            sa.ForeignKey("public.runs.run_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("contract_json", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("contract_id", "revision", name="uq_contract_revisions_revision"),
        schema="public",
    )
    op.create_index(
        "ix_contract_revisions_run_id",
        "contract_revisions",
        ["run_id"],
        schema="public",
    )
    op.create_table(
        "gate_interrupts",
        sa.Column("gate_id", sa.String(64), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(64),
            sa.ForeignKey("public.runs.run_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("gate_name", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("run_id", "gate_name", "status", name="uq_gate_interrupts_status"),
        schema="public",
    )
    op.create_index("ix_gate_interrupts_run_id", "gate_interrupts", ["run_id"], schema="public")
    op.create_table(
        "gate_responses",
        sa.Column("response_id", sa.String(64), primary_key=True),
        sa.Column(
            "gate_id",
            sa.String(64),
            sa.ForeignKey("public.gate_interrupts.gate_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            sa.String(64),
            sa.ForeignKey("public.runs.run_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("teacher_id", sa.String(64), nullable=False),
        sa.Column("response_json", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("gate_id", name="uq_gate_responses_gate_id"),
        schema="public",
    )
    op.create_index("ix_gate_responses_run_id", "gate_responses", ["run_id"], schema="public")
    op.create_table(
        "artifact_workflows",
        sa.Column("workflow_id", sa.String(64), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(64),
            sa.ForeignKey("public.runs.run_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("artifact_id", sa.String(64), nullable=False),
        sa.Column("artifact_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("snapshot_id", sa.String(64), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("run_id", "artifact_id", name="uq_artifact_workflows_artifact"),
        schema="public",
    )
    op.create_index(
        "ix_artifact_workflows_run_id",
        "artifact_workflows",
        ["run_id"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_artifact_workflows_run_id", table_name="artifact_workflows", schema="public")
    op.drop_table("artifact_workflows", schema="public")
    op.drop_index("ix_gate_responses_run_id", table_name="gate_responses", schema="public")
    op.drop_table("gate_responses", schema="public")
    op.drop_index("ix_gate_interrupts_run_id", table_name="gate_interrupts", schema="public")
    op.drop_table("gate_interrupts", schema="public")
    op.drop_index("ix_contract_revisions_run_id", table_name="contract_revisions", schema="public")
    op.drop_table("contract_revisions", schema="public")
    op.drop_table("run_contracts", schema="public")
