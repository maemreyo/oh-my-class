"""Notification CRUD store.

Provides create, query, mark-read, and dismiss operations with
deduplication: the same (run_id, event_type) pair will not produce
duplicate notifications, and the same (notification_id, channel) pair
will not produce duplicate deliveries.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from services.gateway.notification_db import Notification, NotificationDeliveryRecord

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def create_notification(
    event: NotificationEvent,
    db: AsyncSession,
) -> str:
    """Insert a notification, deduplicating on (run_id, event_type).

    Returns the notification_id (new or existing).
    """
    # Deduplicate: if same run_id + event_type already exists, return existing
    existing = await _find_existing_notification(
        event.run_id, event.event_type, db,
    )
    if existing is not None:
        return existing

    notification = Notification(
        id=event.event_id,
        run_id=event.run_id,
        teacher_id=event.teacher_id,
        event_type=event.event_type,
        title=event.title,
        message=event.message,
        metadata_json=json.dumps(event.metadata),
        created_at=event.created_at,
    )
    db.add(notification)
    await db.flush()
    return event.event_id


async def deliver_notification(
    notification_id: str,
    channel: str,
    db: AsyncSession,
) -> str:
    """Insert a delivery record, skipping if already delivered.

    Returns the delivery_id.
    """
    existing = await _find_existing_delivery(notification_id, channel, db)
    if existing is not None:
        return existing.id

    delivery_id = f"del-{notification_id[:12]}-{channel}"
    delivery = NotificationDeliveryRecord(
        id=delivery_id,
        notification_id=notification_id,
        channel=channel,
        status="delivered",
        delivered_at=datetime.now(UTC),
    )
    db.add(delivery)
    await db.flush()
    return delivery_id


async def get_notifications(
    teacher_id: str,
    db: AsyncSession,
    *,
    unread_only: bool = False,
) -> list[dict[str, object]]:
    """Query notifications for a teacher, newest first."""
    statement = (
        select(Notification)
        .where(Notification.teacher_id == teacher_id)
        .order_by(Notification.created_at.desc())
    )
    if unread_only:
        statement = statement.where(Notification.read_at.is_(None))

    result = await db.execute(statement)
    notifications = result.scalars().all()

    return [
        {
            "notification_id": n.id,
            "run_id": n.run_id,
            "teacher_id": n.teacher_id,
            "event_type": n.event_type,
            "title": n.title,
            "message": n.message,
            "metadata": json.loads(n.metadata_json) if n.metadata_json else {},
            "created_at": n.created_at,
            "read_at": n.read_at,
        }
        for n in notifications
    ]


async def mark_read(notification_id: str, db: AsyncSession) -> None:
    """Set read_at = now() for the given notification."""
    statement = select(Notification).where(Notification.id == notification_id)
    result = await db.execute(statement)
    notification = result.scalar_one_or_none()
    if notification is None:
        return
    notification.read_at = datetime.now(UTC)
    await db.flush()


async def dismiss_notification(
    notification_id: str,
    channel: str,
    db: AsyncSession,
) -> None:
    """Update delivery status to 'dismissed'."""
    statement = select(NotificationDeliveryRecord).where(
        NotificationDeliveryRecord.notification_id == notification_id,
        NotificationDeliveryRecord.channel == channel,
    )
    result = await db.execute(statement)
    delivery = result.scalar_one_or_none()
    if delivery is None:
        return
    delivery.status = "dismissed"
    await db.flush()


async def _find_existing_notification(
    run_id: str,
    event_type: str,
    db: AsyncSession,
) -> str | None:
    statement = select(Notification.id).where(
        Notification.run_id == run_id,
        Notification.event_type == event_type,
    ).limit(1)
    result = await db.execute(statement)
    return result.scalar_one_or_none()


async def _find_existing_delivery(
    notification_id: str,
    channel: str,
    db: AsyncSession,
) -> NotificationDeliveryRecord | None:
    statement = select(NotificationDeliveryRecord).where(
        NotificationDeliveryRecord.notification_id == notification_id,
        NotificationDeliveryRecord.channel == channel,
    ).limit(1)
    result = await db.execute(statement)
    return result.scalar_one_or_none()


# Re-export the event type for convenience
from services.gateway.notification_models import NotificationEvent  # noqa: E402
