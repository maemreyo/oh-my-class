"""Add vocabulary cluster workflow persistence.

Revision ID: 019_vocabulary_cluster_workflows
Revises: 018_template_effectiveness
Create Date: 2026-07-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
import alembic.op as op

revision: str = "019_vocabulary_cluster_workflows"
down_revision: str | None = "018_template_effectiveness"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vocabulary_cluster_workflows",
        sa.Column("workflow_id", sa.String(120), primary_key=True),
        sa.Column("cluster_id", sa.String(120), nullable=False),
        sa.Column("run_id", sa.String(64), sa.ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("normalized_input", sa.JSON(), nullable=False),
        sa.Column("raw_input_span", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("review_status", sa.String(32), nullable=False),
        sa.Column("export_refs", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("snapshot_hash", sa.String(64), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("run_id", "cluster_id", name="uq_vocabulary_cluster_workflows_cluster"),
        schema="public",
    )
    op.create_index(
        "ix_vocabulary_cluster_workflows_run_id",
        "vocabulary_cluster_workflows",
        ["run_id"],
        schema="public",
    )
    op.create_table(
        "vocabulary_cluster_evidence",
        sa.Column("evidence_id", sa.String(120), primary_key=True),
        sa.Column(
            "workflow_id",
            sa.String(120),
            sa.ForeignKey("public.vocabulary_cluster_workflows.workflow_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("cluster_id", sa.String(120), nullable=False),
        sa.Column("run_id", sa.String(64), sa.ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("workflow_id", "sequence", name="uq_vocabulary_cluster_evidence_sequence"),
        schema="public",
    )
    op.create_index(
        "ix_vocabulary_cluster_evidence_run_cluster",
        "vocabulary_cluster_evidence",
        ["run_id", "cluster_id"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_vocabulary_cluster_evidence_run_cluster", table_name="vocabulary_cluster_evidence", schema="public")
    op.drop_table("vocabulary_cluster_evidence", schema="public")
    op.drop_index("ix_vocabulary_cluster_workflows_run_id", table_name="vocabulary_cluster_workflows", schema="public")
    op.drop_table("vocabulary_cluster_workflows", schema="public")
