"""Fan-out dispatcher — sends to all available channels concurrently."""
from __future__ import annotations
import asyncio
import logging
from packages.notifications.base import ApprovalEvent, NotificationChannel

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    def __init__(self, channels: list):
        self.channels = channels

    async def notify(self, event: ApprovalEvent) -> dict[str, bool]:
        """Send to all available channels concurrently."""
        available = []
        for ch in self.channels:
            try:
                if await ch.is_available():
                    available.append(ch)
            except Exception as exc:
                logger.warning("Channel %s availability check failed: %s", ch.name, exc)

        if not available:
            return {}

        results = await asyncio.gather(
            *[ch.send(event) for ch in available],
            return_exceptions=True,
        )
        return {
            ch.name: (result is True)
            for ch, result in zip(available, results)
        }
