"""Notifications and delivery tracking tables.

Revision ID: 008_notifications
Revises: 007_soft_delete_and_retention
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "008_notifications"
down_revision: str | None = "007_soft_delete_and_retention"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(64),
            sa.ForeignKey("public.runs.run_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("teacher_id", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("metadata_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_notifications_run_id",
        "notifications",
        ["run_id"],
        schema="public",
    )
    op.create_index(
        "ix_notifications_teacher_id",
        "notifications",
        ["teacher_id"],
        schema="public",
    )
    op.create_index(
        "ix_notifications_teacher_created",
        "notifications",
        ["teacher_id", "created_at"],
        schema="public",
    )

    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "notification_id",
            sa.String(64),
            sa.ForeignKey("public.notifications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "notification_id",
            "channel",
            name="uq_notification_deliveries_notification_channel",
        ),
        schema="public",
    )
    op.create_index(
        "ix_notification_deliveries_notification_id",
        "notification_deliveries",
        ["notification_id"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_deliveries_notification_id",
        schema="public",
    )
    op.drop_table("notification_deliveries", schema="public")
    op.drop_index("ix_notifications_teacher_created", schema="public")
    op.drop_index("ix_notifications_teacher_id", schema="public")
    op.drop_index("ix_notifications_run_id", schema="public")
    op.drop_table("notifications", schema="public")
