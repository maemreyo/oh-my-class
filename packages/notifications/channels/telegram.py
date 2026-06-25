"""Telegram bot notification channel. Free, no SDK needed."""
from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from packages.notifications.base import ApprovalEvent


class TelegramConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TELEGRAM_", env_file=".env", extra="ignore")
    bot_token: str = ""
    chat_id: str = ""


class TelegramChannel:
    name = "telegram"

    def __init__(self, config: TelegramConfig | None = None):
        self._config = config or TelegramConfig()

    async def is_available(self) -> bool:
        return bool(self._config.bot_token and self._config.chat_id)

    async def send(self, event: ApprovalEvent) -> bool:
        if not await self.is_available():
            return False

        text = self._format(event)
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{self._config.bot_token}/sendMessage",
                json={
                    "chat_id": self._config.chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                },
                timeout=10.0,
            )
        return resp.status_code == 200

    def _format(self, event: ApprovalEvent) -> str:
        score_line = f"Judge score: {event.judge_score:.1f}/10\n" if event.judge_score else ""
        return (
            f"*Approval Required*\n\n"
            f"{event.summary}\n\n"
            f"{score_line}"
            f"Gate: `{event.gate_type}`\n"
            f"Run: `{event.run_id}`\n\n"
            f"[Open Dashboard]({event.approve_url})\n\n"
            f"Expires in {event.expires_in_hours}h"
        )
