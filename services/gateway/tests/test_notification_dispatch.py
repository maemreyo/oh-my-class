from __future__ import annotations

from fastapi import FastAPI
from starlette.testclient import TestClient

from services.gateway.routers.webhooks import WebhookDispatch, router


class RecordingDispatcher:
    def __init__(self) -> None:
        self.events: list[WebhookDispatch] = []

    async def dispatch(self, event: WebhookDispatch) -> None:
        self.events.append(event)


class TestNotificationDispatch:
    def test_notify_dispatches_when_secret_is_valid(self, monkeypatch) -> None:
        monkeypatch.setenv("WEBHOOK_NOTIFY_SECRET", "notify-secret")
        dispatcher = RecordingDispatcher()
        client = _client(dispatcher)

        response = client.post(
            "/webhook/notify",
            json={"event_id": "notify-gate", "type": "gate_pending", "run_id": "run-1"},
            headers={"X-Webhook-Secret": "notify-secret"},
        )

        assert response.status_code == 200
        assert response.json() == {"status": "dispatched", "type": "gate_pending"}
        assert [(event.source, event.event_type, event.event_id) for event in dispatcher.events] == [
            ("notify", "gate_pending", "notify-gate"),
        ]

    def test_notify_rejects_invalid_secret_without_dispatch(self, monkeypatch) -> None:
        monkeypatch.setenv("WEBHOOK_NOTIFY_SECRET", "notify-secret")
        dispatcher = RecordingDispatcher()
        client = _client(dispatcher)

        response = client.post(
            "/webhook/notify",
            json={"event_id": "notify-fail", "type": "failure"},
            headers={"X-Webhook-Secret": "wrong"},
        )

        assert response.status_code == 403
        assert dispatcher.events == []

    def test_zalo_effectiveness_event_is_ingested_after_dispatch(self, monkeypatch) -> None:
        monkeypatch.setenv("ZALO_WEBHOOK_SECRET", "zalo-secret")
        dispatcher = RecordingDispatcher()
        app = FastAPI()
        app.state.webhook_dispatcher = dispatcher
        app.include_router(router, prefix="/webhook")
        client = TestClient(app)
        payload = {"event_id": "effectiveness-1", "type": "effectiveness_response", "score": 0.8}

        response = client.post("/webhook/zalo", json=payload, headers={"X-Webhook-Secret": "zalo-secret"})

        assert response.status_code == 200
        assert dispatcher.events[0].event_type == "effectiveness_response"
        assert app.state.effectiveness_ingestion_events == [payload]


def _client(dispatcher: RecordingDispatcher) -> TestClient:
    app = FastAPI()
    app.state.webhook_dispatcher = dispatcher
    app.include_router(router, prefix="/webhook")
    return TestClient(app)
