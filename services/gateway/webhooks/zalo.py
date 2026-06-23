"""Zalo webhook shared secret verification."""

import os


def get_zalo_secret() -> str | None:
    """Get Zalo webhook secret from environment."""
    return os.environ.get("ZALO_WEBHOOK_SECRET")


def verify_zalo_signature(provided_secret: str | None) -> bool:
    """Verify Zalo webhook using shared secret in X-Webhook-Secret header."""
    expected = get_zalo_secret()
    if not expected:
        # If no secret configured, skip verification (dev mode)
        return True

    if not provided_secret:
        return False

    return provided_secret == expected
