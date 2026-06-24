"""SSE channel — pushes event to existing RunStream."""
from __future__ import annotations
from packages.notifications.base import ApprovalEvent


class SSEChannel:
    """Triggers ApprovalModal via existing SSE infrastructure."""
    name = "sse"

    def __init__(self, stream_manager=None):
        self._stream = stream_manager

    async def is_available(self) -> bool:
        return True  # always available

    async def send(self, event: ApprovalEvent) -> bool:
        if self._stream:
            await self._stream.publish(event.run_id, {
                "type": "interrupt",
                "gate": event.gate_type,
                "run_id": event.run_id,
                "summary": event.summary,
            })
        return True
