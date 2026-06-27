"""Domain models for the notification system.

Pure dataclasses — no ORM, no framework dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


NotificationType = Literal[
    "clarification_required",
    "contract_confirmation",
    "search_confirmation",
    "blueprint_ready",
    "content_preview_ready",
    "run_completed",
    "run_failed",
    "run_escalated",
    "gate_timeout_warning",
]

NotificationChannel = Literal["in_app", "email", "zalo", "telegram"]

DeliveryStatus = Literal["pending", "delivered", "failed", "dismissed"]


@dataclass(frozen=True, slots=True)
class NotificationEvent:
    """A single notification event to be delivered."""

    event_id: str
    run_id: str
    teacher_id: str
    event_type: NotificationType
    title: str
    message: str
    metadata: dict[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now())


@dataclass(frozen=True, slots=True)
class NotificationDelivery:
    """A delivery attempt for a notification on a specific channel."""

    delivery_id: str
    notification_id: str
    channel: NotificationChannel
    status: DeliveryStatus = "pending"
    delivered_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now())
