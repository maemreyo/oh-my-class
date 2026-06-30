from __future__ import annotations

from fastapi import FastAPI
from starlette.testclient import TestClient

from services.gateway.routers.webhooks import WebhookDispatch, router


class RecordingDispatcher:
    def __init__(self) -> None:
        self.events: list[WebhookDispatch] = []

    async def dispatch(self, event: WebhookDispatch) -> None:
        self.events.append(event)


class TestWebhookIdempotency:
    def test_redelivered_zalo_event_is_processed_once(self, monkeypatch) -> None:
        monkeypatch.setenv("ZALO_WEBHOOK_SECRET", "zalo-secret")
        dispatcher = RecordingDispatcher()
        client = _client(dispatcher)
        payload = {"event_id": "retry-1", "type": "gate_pending"}

        first = client.post("/webhook/zalo", json=payload, headers={"X-Webhook-Secret": "zalo-secret"})
        second = client.post("/webhook/zalo", json=payload, headers={"X-Webhook-Secret": "zalo-secret"})

        assert first.json() == {"status": "processed"}
        assert second.json() == {"status": "duplicate"}
        assert [event.event_id for event in dispatcher.events] == ["zalo:retry-1"]

    def test_rate_limit_trips_per_source(self, monkeypatch) -> None:
        monkeypatch.setenv("ZALO_WEBHOOK_SECRET", "zalo-secret")
        monkeypatch.setenv("WEBHOOK_RATE_LIMIT_COUNT", "1")
        monkeypatch.setenv("WEBHOOK_RATE_LIMIT_WINDOW_SECONDS", "60")
        dispatcher = RecordingDispatcher()
        client = _client(dispatcher)

        first = client.post(
            "/webhook/zalo",
            json={"event_id": "flood-1", "type": "gate_pending"},
            headers={"X-Webhook-Secret": "zalo-secret"},
        )
        second = client.post(
            "/webhook/zalo",
            json={"event_id": "flood-2", "type": "gate_pending"},
            headers={"X-Webhook-Secret": "zalo-secret"},
        )

        assert first.status_code == 200
        assert second.status_code == 429
        assert [event.event_id for event in dispatcher.events] == ["zalo:flood-1"]


def _client(dispatcher: RecordingDispatcher) -> TestClient:
    app = FastAPI()
    app.state.webhook_dispatcher = dispatcher
    app.include_router(router, prefix="/webhook")
    return TestClient(app)
