"""Webhook notifications — Telegram, Zalo, email alerts for teacher gates."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import hashlib
from typing import Any, Protocol

import httpx2

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from ..logging_config import bind_context, get_logger
from ..webhooks.config import webhook_config
from ..webhooks.telegram import verify_telegram_signature
from ..webhooks.zalo import verify_zalo_signature

router = APIRouter()


@dataclass(frozen=True, slots=True)
class WebhookDispatch:
    source: str
    event_id: str
    event_type: str
    payload: dict[str, Any]


class WebhookDispatcher(Protocol):
    async def dispatch(self, event: WebhookDispatch) -> None: ...


@dataclass(slots=True)
class WebhookProcessingState:
    processed_event_ids: set[str] = field(default_factory=set)
    request_times_by_source: dict[str, list[datetime]] = field(default_factory=dict)


class LoggingWebhookDispatcher:
    async def dispatch(self, event: WebhookDispatch) -> None:
        get_logger("webhook.dispatch").info(
            "webhook.dispatched source=%s event_type=%s event_id=%s",
            event.source,
            event.event_type,
            event.event_id,
        )


@dataclass(frozen=True, slots=True)
class OutboundWebhookDispatcher:
    urls: tuple[str, ...]
    retries: int = 2

    async def dispatch(self, event: WebhookDispatch) -> None:
        if not self.urls:
            await LoggingWebhookDispatcher().dispatch(event)
            return
        async with httpx2.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            for url in self.urls:
                await _post_with_retry(client, url, event, self.retries)


@router.post("/notify")  # pyright: ignore[reportUntypedFunctionDecorator]
async def send_notification(request: Request):
    """POST /webhook/notify — Send gate approval notification.

    Accepts JSON payload describing the notification event.
    Returns ack; actual dispatch (Telegram/Zalo/email) is TODO.
    """
    secret = request.headers.get("X-Webhook-Secret")
    if not _verify_notify_secret(secret):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid notify webhook secret")
    payload = await request.json()
    event = WebhookDispatch(
        source="notify",
        event_id=_event_id(payload),
        event_type=str(payload.get("type", "unknown")),
        payload=payload,
    )
    await _dispatcher(request).dispatch(event)
    get_logger("webhook.notify").info(
        "notify.received type=%s payload_keys=%s",
        payload.get("type", "unknown"),
        list(payload.keys()),
    )
    return {"status": "dispatched", "type": payload.get("type", "unknown")}


@router.post("/telegram")  # pyright: ignore[reportUntypedFunctionDecorator]
async def telegram_webhook(request: Request):
    """POST /webhook/telegram — Receive Telegram bot updates.

    Verifies X-Telegram-Bot-Api-Secret-Token header using HMAC-SHA256.
    """
    body = await request.body()
    signature = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")

    if not verify_telegram_signature(body, signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Telegram webhook signature",
        )

    payload = await request.json()
    result = await _process_verified_webhook(request, "telegram", payload, body)
    return {"status": result}


@router.post("/zalo")  # pyright: ignore[reportUntypedFunctionDecorator]
async def zalo_webhook(request: Request):
    """POST /webhook/zalo — Receive Zalo webhook events.

    Verifies X-Webhook-Secret header using shared secret.
    """
    secret = request.headers.get("X-Webhook-Secret")

    if not verify_zalo_signature(secret):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Zalo webhook secret",
        )

    payload = await request.json()
    result = await _process_verified_webhook(request, "zalo", payload, None)
    if result == "processed" and payload.get("type") == "effectiveness_response":
        _effectiveness_events(request).append(payload)
    return {"status": result}


async def _process_verified_webhook(
    request: Request,
    source: str,
    payload: dict[str, Any],
    body: bytes | None,
) -> str:
    state = _processing_state(request)
    if not _allow_request(state, source, datetime.now(UTC)):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="webhook_rate_limited")
    event_id = f"{source}:{_event_id(payload, body)}"
    if event_id in state.processed_event_ids:
        return "duplicate"
    state.processed_event_ids.add(event_id)
    await _dispatcher(request).dispatch(WebhookDispatch(
        source=source,
        event_id=event_id,
        event_type=str(payload.get("type", payload.get("event", "unknown"))),
        payload=payload,
    ))
    return "processed"


def _processing_state(request: Request) -> WebhookProcessingState:
    state = getattr(request.app.state, "webhook_processing_state", None)
    if isinstance(state, WebhookProcessingState):
        return state
    state = WebhookProcessingState()
    request.app.state.webhook_processing_state = state
    return state


def _dispatcher(request: Request) -> WebhookDispatcher:
    dispatcher = getattr(request.app.state, "webhook_dispatcher", None)
    if dispatcher is not None:
        return dispatcher
    urls = _outbound_webhook_urls()
    dispatcher = OutboundWebhookDispatcher(urls=urls) if urls else LoggingWebhookDispatcher()
    request.app.state.webhook_dispatcher = dispatcher
    return dispatcher


async def _post_with_retry(
    client: httpx2.AsyncClient,
    url: str,
    event: WebhookDispatch,
    retries: int,
) -> None:
    last_error: httpx2.HTTPError | None = None
    for _ in range(retries + 1):
        try:
            response = await client.post(url, json=_dispatch_payload(event))
            response.raise_for_status()
            return
        except httpx2.HTTPError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error


def _dispatch_payload(event: WebhookDispatch) -> dict[str, Any]:
    return {
        "source": event.source,
        "event_id": event.event_id,
        "event_type": event.event_type,
        "payload": event.payload,
    }


def _outbound_webhook_urls() -> tuple[str, ...]:
    raw = webhook_config().webhook_outbound_urls
    return tuple(url.strip() for url in raw.split(",") if url.strip())


def _effectiveness_events(request: Request) -> list[dict[str, Any]]:
    events = getattr(request.app.state, "effectiveness_ingestion_events", None)
    if isinstance(events, list):
        return events
    events = []
    request.app.state.effectiveness_ingestion_events = events
    return events


def _allow_request(state: WebhookProcessingState, source: str, now: datetime) -> bool:
    window = timedelta(seconds=_rate_window_seconds())
    recent = [seen_at for seen_at in state.request_times_by_source.get(source, []) if now - seen_at <= window]
    if len(recent) >= _rate_limit_count():
        state.request_times_by_source[source] = recent
        return False
    recent.append(now)
    state.request_times_by_source[source] = recent
    return True


def _event_id(payload: dict[str, Any], body: bytes | None = None) -> str:
    for key in ("event_id", "update_id", "message_id", "id"):
        value = payload.get(key)
        if value is not None:
            return str(value)
    raw = body if body is not None else repr(sorted(payload.items())).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _verify_notify_secret(secret: str | None) -> bool:
    expected = webhook_config().webhook_notify_secret
    return bool(expected and secret and secret == expected)


def _rate_limit_count() -> int:
    return webhook_config().webhook_rate_limit_count


def _rate_window_seconds() -> int:
    return webhook_config().webhook_rate_limit_window_seconds


class FrontendErrorReport(BaseModel):
    """Payload posted by the frontend when an error is caught client-side.

    The frontend ``useErrorLogger`` hook fires this as a fire-and-forget
    request so the gateway can log the failure with the full request
    context (request_id, url, component stack) for correlation with
    server-side logs.
    """

    message: str = Field(..., min_length=1, max_length=1000)
    component_stack: str | None = None
    error_message: str | None = None
    request_id: str | None = None
    url: str | None = None
    user_agent: str | None = None
    timestamp: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


@router.post("/error")  # pyright: ignore[reportUntypedFunctionDecorator]
async def frontend_error(report: FrontendErrorReport, request: Request):
    """POST /webhook/error — Receive frontend error reports.

    Logs the error with full context. Fire-and-forget endpoint.
    """
    log = get_logger("frontend.error")
    log = bind_context(
        log,
        request_id=report.request_id or getattr(request.state, "request_id", None),
    )
    log.error(
        "frontend_error frontend_message=%r error_message=%r url=%r component_stack=%r",
        report.message,
        report.error_message,
        report.url,
        report.component_stack,
    )
    return {"status": "received"}
