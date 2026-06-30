from __future__ import annotations

import hashlib
import hmac

from fastapi import FastAPI
from starlette.testclient import TestClient

from services.gateway.routers.webhooks import WebhookDispatch, router


class RecordingDispatcher:
    def __init__(self) -> None:
        self.events: list[WebhookDispatch] = []

    async def dispatch(self, event: WebhookDispatch) -> None:
        self.events.append(event)


class TestWebhookSignatureGate:
    def test_telegram_rejects_unsigned_payload_when_secret_configured(self, monkeypatch) -> None:
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "telegram-secret")
        dispatcher = RecordingDispatcher()
        client = _client(dispatcher)

        response = client.post("/webhook/telegram", json={"update_id": "update-1"})

        assert response.status_code == 403
        assert dispatcher.events == []

    def test_telegram_processes_valid_signature(self, monkeypatch) -> None:
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "telegram-secret")
        dispatcher = RecordingDispatcher()
        client = _client(dispatcher)
        body = b'{"update_id":"update-1","type":"gate_pending"}'
        signature = hmac.HMAC(b"telegram-secret", body, hashlib.sha256).hexdigest()

        response = client.post(
            "/webhook/telegram",
            content=body,
            headers={"X-Telegram-Bot-Api-Secret-Token": signature, "Content-Type": "application/json"},
        )

        assert response.status_code == 200
        assert response.json() == {"status": "processed"}
        assert [event.event_id for event in dispatcher.events] == ["telegram:update-1"]

    def test_zalo_fails_closed_when_secret_is_missing(self, monkeypatch) -> None:
        monkeypatch.delenv("ZALO_WEBHOOK_SECRET", raising=False)
        dispatcher = RecordingDispatcher()
        client = _client(dispatcher)

        response = client.post("/webhook/zalo", json={"event_id": "zalo-1"})

        assert response.status_code == 403
        assert dispatcher.events == []

    def test_zalo_processes_valid_secret(self, monkeypatch) -> None:
        monkeypatch.setenv("ZALO_WEBHOOK_SECRET", "zalo-secret")
        dispatcher = RecordingDispatcher()
        client = _client(dispatcher)

        response = client.post(
            "/webhook/zalo",
            json={"event_id": "zalo-1", "type": "completion"},
            headers={"X-Webhook-Secret": "zalo-secret"},
        )

        assert response.status_code == 200
        assert response.json() == {"status": "processed"}
        assert [event.event_id for event in dispatcher.events] == ["zalo:zalo-1"]


def _client(dispatcher: RecordingDispatcher) -> TestClient:
    app = FastAPI()
    app.state.webhook_dispatcher = dispatcher
    app.include_router(router, prefix="/webhook")
    return TestClient(app)
