"""Webhook configuration — pydantic-settings, not bare os.environ (LGH-06).

Field names match their env vars by pydantic-settings' default snake_case ->
SCREAMING_SNAKE_CASE convention (no env_prefix — these vars don't share one).
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class WebhookConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    telegram_webhook_secret: str | None = None
    zalo_webhook_secret: str | None = None
    webhook_outbound_urls: str = ""
    webhook_notify_secret: str | None = None
    webhook_rate_limit_count: int = 60
    webhook_rate_limit_window_seconds: int = 60


def webhook_config() -> WebhookConfig:
    # ponytail: uncached, same reasoning as auth/config.py's jwt_config().
    return WebhookConfig()
