"""Initial schema — create public, langgraph, litellm schemas and tables.

Revision ID: 001_initial
Revises: None
Create Date: 2026-06-23
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create schemas
    op.execute("CREATE SCHEMA IF NOT EXISTS public")
    op.execute("CREATE SCHEMA IF NOT EXISTS langgraph")
    op.execute("CREATE SCHEMA IF NOT EXISTS litellm")

    # Users table
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(64), primary_key=True),
        sa.Column("username", sa.String(128), unique=True, nullable=False),
        sa.Column("email", sa.String(256), nullable=True),
        sa.Column("role", sa.Enum("teacher", "admin", name="userrole"),
                  nullable=False, server_default="teacher"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("last_login", sa.DateTime, nullable=True),
        schema="public",
    )

    # Runs table
    op.create_table(
        "runs",
        sa.Column("run_id", sa.String(64), primary_key=True),
        sa.Column("teacher_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("current_step", sa.Integer, server_default="1"),
        sa.Column("raw_request", sa.Text, nullable=False),
        sa.Column("class_info", sa.JSON, nullable=True),
        sa.Column("lesson_plan", sa.JSON, nullable=True),
        sa.Column("artifact_types", sa.JSON, nullable=True),
        sa.Column("theme", sa.String(32), server_default="default"),
        sa.Column("quality_scores", sa.JSON, nullable=True),
        sa.Column("quality_passed", sa.Boolean, server_default="false"),
        sa.Column("teacher_approved", sa.Boolean, server_default="false"),
        sa.Column("revision_count", sa.Integer, server_default="0"),
        sa.Column("revision_feedback", sa.Text, nullable=True),
        sa.Column("export_formats", sa.JSON, nullable=True),
        sa.Column("tokens_used", sa.Integer, server_default="0"),
        sa.Column("cost_usd", sa.Float, server_default="0.0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        schema="public",
    )

    # Artifacts table
    op.create_table(
        "artifacts",
        sa.Column("artifact_id", sa.String(64), primary_key=True),
        sa.Column("run_id", sa.String(64), nullable=False),
        sa.Column("artifact_type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("theme", sa.String(32), server_default="default"),
        sa.Column("content_json", sa.JSON, nullable=True),
        sa.Column("rendered_html", sa.Text, nullable=True),
        sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        schema="public",
    )

    # Cost logs table (in litellm schema)
    op.create_table(
        "cost_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(64), nullable=False),
        sa.Column("agent", sa.String(64), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("prompt_tokens", sa.Integer, server_default="0"),
        sa.Column("completion_tokens", sa.Integer, server_default="0"),
        sa.Column("cost_usd", sa.Float, server_default="0.0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        schema="litellm",
    )

    # Create indexes
    op.create_index("ix_runs_teacher_id", "runs", ["teacher_id"], schema="public")
    op.create_index("ix_runs_status", "runs", ["status"], schema="public")
    op.create_index("ix_artifacts_run_id", "artifacts", ["run_id"], schema="public")
    op.create_index("ix_cost_logs_run_id", "cost_logs", ["run_id"], schema="litellm")


def downgrade() -> None:
    op.drop_table("cost_logs", schema="litellm")
    op.drop_table("artifacts", schema="public")
    op.drop_table("runs", schema="public")
    op.drop_table("users", schema="public")

    op.execute("DROP SCHEMA IF EXISTS litellm")
    op.execute("DROP SCHEMA IF EXISTS langgraph")
    # Don't drop public — it's the default schema
