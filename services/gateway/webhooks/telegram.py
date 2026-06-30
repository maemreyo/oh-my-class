"""Telegram webhook signature verification using HMAC-SHA256."""

import hashlib
import hmac
import os


def get_telegram_secret() -> str | None:
    """Get Telegram webhook secret from environment."""
    return os.environ.get("TELEGRAM_WEBHOOK_SECRET")


def verify_telegram_signature(body: bytes, signature: str) -> bool:
    """Verify Telegram webhook HMAC-SHA256 signature.

    Telegram sends signature in header: X-Telegram-Bot-Api-Secret-Token
    """
    secret = get_telegram_secret()
    if not secret:
        return False

    expected = hmac.HMAC(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)
