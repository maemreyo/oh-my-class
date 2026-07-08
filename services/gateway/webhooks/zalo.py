"""Zalo webhook shared secret verification."""

from services.gateway.webhooks.config import webhook_config


def get_zalo_secret() -> str | None:
    """Get Zalo webhook secret from environment."""
    return webhook_config().zalo_webhook_secret


def verify_zalo_signature(provided_secret: str | None) -> bool:
    """Verify Zalo webhook using shared secret in X-Webhook-Secret header."""
    expected = get_zalo_secret()
    if not expected:
        return False

    if not provided_secret:
        return False

    return provided_secret == expected
