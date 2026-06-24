from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class ApprovalEvent:
    run_id: str
    teacher_id: str
    gate_type: str          # "blueprint_approval" | "content_approval"
    summary: str            # human-readable summary of what needs approval
    approve_url: str        # deep link into dashboard
    artifacts_count: int = 0
    judge_score: float | None = None
    expires_in_hours: int = 24


@runtime_checkable
class NotificationChannel(Protocol):
    """Every channel implements exactly this interface."""
    name: str

    async def send(self, event: ApprovalEvent) -> bool:
        """Send notification. Returns True on success."""
        ...

    async def is_available(self) -> bool:
        """Check if channel is configured and reachable."""
        ...
