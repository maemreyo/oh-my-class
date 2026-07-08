"""LGH-06 Phase 1: auth/webhook config now loads via pydantic-settings, not
bare os.environ. Covers the load-order gap that caused the original bug (a
bare Python process vs. one that inherited env from docker-compose/gateway
startup) and confirms secrets still fail loudly, not silently default."""
from __future__ import annotations

import pytest


def test_jwt_secret_missing_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    """Note: pydantic-settings reads the real .env file too (not just process
    env), so a bare monkeypatch.delenv doesn't simulate "unset" if the repo's
    own .env has a value — that's the whole point of this migration (a bare
    process now sees the real secret instead of silently seeing nothing).
    Force an explicit empty override to simulate the genuinely-unconfigured case."""
    from services.gateway.auth.jwt_handler import get_jwt_secret

    monkeypatch.setenv("JWT_SECRET", "")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        get_jwt_secret()


def test_jwt_config_reads_from_process_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.gateway.auth.jwt_handler import (
        get_jwt_algorithm,
        get_jwt_expiry_hours,
        get_jwt_secret,
    )

    monkeypatch.setenv("JWT_SECRET", "test-secret-minimum-32-characters")
    monkeypatch.setenv("JWT_ALGORITHM", "HS512")
    monkeypatch.setenv("JWT_EXPIRY_HOURS", "48")

    assert get_jwt_secret() == "test-secret-minimum-32-characters"
    assert get_jwt_algorithm() == "HS512"
    assert get_jwt_expiry_hours() == 48


def test_jwt_config_defaults_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.gateway.auth.jwt_handler import get_jwt_algorithm, get_jwt_expiry_hours

    monkeypatch.delenv("JWT_ALGORITHM", raising=False)
    monkeypatch.delenv("JWT_EXPIRY_HOURS", raising=False)

    assert get_jwt_algorithm() == "HS256"
    assert get_jwt_expiry_hours() == 24


def test_webhook_config_reads_vars_with_no_shared_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    """WebhookConfig has no env_prefix — TELEGRAM_/ZALO_/WEBHOOK_ vars share no
    common prefix, so each field maps to its own bare uppercased name."""
    from services.gateway.webhooks.config import webhook_config

    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "telegram-secret")
    monkeypatch.setenv("ZALO_WEBHOOK_SECRET", "zalo-secret")
    monkeypatch.setenv("WEBHOOK_OUTBOUND_URLS", "https://a.example,https://b.example")
    monkeypatch.setenv("WEBHOOK_NOTIFY_SECRET", "notify-secret")
    monkeypatch.setenv("WEBHOOK_RATE_LIMIT_COUNT", "120")
    monkeypatch.setenv("WEBHOOK_RATE_LIMIT_WINDOW_SECONDS", "30")

    config = webhook_config()

    assert config.telegram_webhook_secret == "telegram-secret"
    assert config.zalo_webhook_secret == "zalo-secret"
    assert config.webhook_outbound_urls == "https://a.example,https://b.example"
    assert config.webhook_notify_secret == "notify-secret"
    assert config.webhook_rate_limit_count == 120
    assert config.webhook_rate_limit_window_seconds == 30


def test_webhook_config_secrets_default_to_none_not_silent_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """See test_jwt_secret_missing_fails_loudly's docstring re: why an explicit
    empty override (not delenv) is needed to simulate "genuinely unconfigured"."""
    from services.gateway.webhooks.telegram import get_telegram_secret, verify_telegram_signature
    from services.gateway.webhooks.zalo import get_zalo_secret, verify_zalo_signature

    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "")
    monkeypatch.setenv("ZALO_WEBHOOK_SECRET", "")

    assert not get_telegram_secret()
    assert not get_zalo_secret()
    # missing secret must fail-closed (reject), never silently accept
    assert verify_telegram_signature(b"body", "any-signature") is False
    assert verify_zalo_signature("any-provided-secret") is False
