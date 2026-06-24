"""Email channel stub — wire up when Resend/SMTP ready."""
from __future__ import annotations
from packages.notifications.base import ApprovalEvent


class EmailChannel:
    name = "email"

    async def is_available(self) -> bool:
        return False  # disabled until configured

    async def send(self, event: ApprovalEvent) -> bool:
        return False
