"""Webhook verification module — Telegram and Zalo signature checking."""

from .telegram import verify_telegram_signature
from .zalo import verify_zalo_signature

__all__ = [
    "verify_telegram_signature",
    "verify_zalo_signature",
]
