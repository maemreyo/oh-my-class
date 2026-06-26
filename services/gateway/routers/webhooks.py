"""Webhook notifications — Telegram, Zalo, email alerts for teacher gates."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from ..logging_config import bind_context, get_logger
from ..webhooks.telegram import verify_telegram_signature
from ..webhooks.zalo import verify_zalo_signature

router = APIRouter()


@router.post("/notify")  # pyright: ignore[reportUntypedFunctionDecorator]
async def send_notification(request: Request):
    """POST /webhook/notify — Send gate approval notification.

    Accepts JSON payload describing the notification event.
    Returns ack; actual dispatch (Telegram/Zalo/email) is TODO.
    """
    payload = await request.json()
    get_logger("webhook.notify").info(
        "notify.received type=%s payload_keys=%s",
        payload.get("type", "unknown"),
        list(payload.keys()),
    )
    return {"status": "received", "type": payload.get("type", "unknown")}


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

    # TODO: Process Telegram update, dispatch to notification handler
    return {"status": "ok"}


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

    # TODO: Process Zalo webhook event
    return {"status": "ok"}


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
