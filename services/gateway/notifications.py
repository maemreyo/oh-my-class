"""In-app notification channel and convenience helpers.

Provides a NotificationChannel protocol and the in-app implementation,
plus helper functions for the most common pipeline notification events.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import uuid4

from services.gateway.logging_config import get_logger
from services.gateway.notification_models import NotificationEvent
from services.gateway.notification_store import create_notification, deliver_notification

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_log = get_logger("notifications")


@runtime_checkable
class NotificationChannel(Protocol):
    """Protocol for notification delivery channels."""

    async def send(
        self,
        notification: NotificationEvent,
        db: AsyncSession,
    ) -> str: ...


class InAppNotificationChannel:
    """Delivers notifications to the in-app notification store."""

    async def send(
        self,
        notification: NotificationEvent,
        db: AsyncSession,
    ) -> str:
        notification_id = await create_notification(notification, db)
        delivery_id = await deliver_notification(notification_id, "in_app", db)
        _log.info(
            "notification.delivered notification_id=%s channel=in_app",
            notification_id,
        )
        return delivery_id


_default_channel = InAppNotificationChannel()


async def notify_gate_required(
    run_id: str,
    teacher_id: str,
    gate_name: str,
    db: AsyncSession,
    *,
    channel: NotificationChannel | None = None,
) -> None:
    """Create and deliver a gate approval notification."""
    ch = channel or _default_channel
    gate_label = gate_name.replace("_", " ").title()
    event = NotificationEvent(
        event_id=str(uuid4()),
        run_id=run_id,
        teacher_id=teacher_id,
        event_type="clarification_required",
        title=f"{gate_label} requires your approval",
        message=(
            f"Your run {run_id} has reached the {gate_label} gate "
            "and needs your review."
        ),
        metadata={"gate_name": gate_name},
    )
    await ch.send(event, db)


async def notify_contract_confirmation(
    run_id: str,
    teacher_id: str,
    db: AsyncSession,
    *,
    channel: NotificationChannel | None = None,
) -> None:
    ch = channel or _default_channel
    await ch.send(NotificationEvent(
        event_id=str(uuid4()),
        run_id=run_id,
        teacher_id=teacher_id,
        event_type="contract_confirmation",
        title="Confirm your run contract",
        message=f"Run {run_id} needs contract confirmation before planning continues.",
        metadata={"gate_name": "contract_confirmation"},
    ), db)


async def notify_search_confirmation(
    run_id: str,
    teacher_id: str,
    db: AsyncSession,
    *,
    channel: NotificationChannel | None = None,
) -> None:
    ch = channel or _default_channel
    await ch.send(NotificationEvent(
        event_id=str(uuid4()),
        run_id=run_id,
        teacher_id=teacher_id,
        event_type="search_confirmation",
        title="Review the research search plan",
        message=f"Run {run_id} needs search plan confirmation.",
        metadata={"gate_name": "search_plan_confirmation"},
    ), db)


async def notify_blueprint_ready(
    run_id: str,
    teacher_id: str,
    db: AsyncSession,
    *,
    channel: NotificationChannel | None = None,
) -> None:
    ch = channel or _default_channel
    await ch.send(NotificationEvent(
        event_id=str(uuid4()),
        run_id=run_id,
        teacher_id=teacher_id,
        event_type="blueprint_ready",
        title="Blueprint ready for review",
        message=f"Run {run_id} has a blueprint ready for approval.",
        metadata={"gate_name": "blueprint_approval"},
    ), db)


async def notify_content_preview_ready(
    run_id: str,
    teacher_id: str,
    snapshot_ids: tuple[str, ...],
    db: AsyncSession,
    *,
    channel: NotificationChannel | None = None,
) -> None:
    ch = channel or _default_channel
    await ch.send(NotificationEvent(
        event_id=str(uuid4()),
        run_id=run_id,
        teacher_id=teacher_id,
        event_type="content_preview_ready",
        title="Content preview ready",
        message=f"Run {run_id} has {len(snapshot_ids)} preview snapshots ready.",
        metadata={"snapshot_ids": list(snapshot_ids)},
    ), db)


async def notify_run_completed(
    run_id: str,
    teacher_id: str,
    db: AsyncSession,
    *,
    channel: NotificationChannel | None = None,
) -> None:
    """Notify teacher that a run completed successfully."""
    ch = channel or _default_channel
    event = NotificationEvent(
        event_id=str(uuid4()),
        run_id=run_id,
        teacher_id=teacher_id,
        event_type="run_completed",
        title="Your teaching pack is ready",
        message=f"Run {run_id} has completed successfully.",
        metadata={},
    )
    await ch.send(event, db)


async def notify_run_failed(
    run_id: str,
    teacher_id: str,
    error: str,
    db: AsyncSession,
    *,
    channel: NotificationChannel | None = None,
) -> None:
    """Notify teacher that a run has failed."""
    ch = channel or _default_channel
    event = NotificationEvent(
        event_id=str(uuid4()),
        run_id=run_id,
        teacher_id=teacher_id,
        event_type="run_failed",
        title="Your run has failed",
        message=f"Run {run_id} failed: {error[:200]}",
        metadata={"error": error[:500]},
    )
    await ch.send(event, db)


async def notify_run_escalated(
    run_id: str,
    teacher_id: str,
    reason: str,
    db: AsyncSession,
    *,
    channel: NotificationChannel | None = None,
) -> None:
    ch = channel or _default_channel
    await ch.send(NotificationEvent(
        event_id=str(uuid4()),
        run_id=run_id,
        teacher_id=teacher_id,
        event_type="run_escalated",
        title="Run escalated for support",
        message=f"Run {run_id} was escalated: {reason[:200]}",
        metadata={"reason": reason[:500]},
    ), db)


async def notify_gate_timeout_warning(
    run_id: str,
    teacher_id: str,
    gate_name: str,
    hours_remaining: int,
    db: AsyncSession,
    *,
    channel: NotificationChannel | None = None,
) -> None:
    ch = channel or _default_channel
    await ch.send(NotificationEvent(
        event_id=str(uuid4()),
        run_id=run_id,
        teacher_id=teacher_id,
        event_type="gate_timeout_warning",
        title="Approval gate timeout warning",
        message=f"Run {run_id} gate {gate_name} expires in {hours_remaining} hours.",
        metadata={"gate_name": gate_name, "hours_remaining": hours_remaining},
    ), db)
