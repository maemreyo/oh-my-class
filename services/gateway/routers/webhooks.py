"""Webhook notifications — Telegram, Zalo, email alerts for teacher gates."""

from fastapi import APIRouter, HTTPException, Request, status

from ..webhooks.telegram import verify_telegram_signature
from ..webhooks.zalo import verify_zalo_signature

router = APIRouter()


@router.post("/notify")
async def send_notification():
    """POST /webhook/notify — Send gate approval notification."""
    # TODO: Dispatch notification via configured channel (Telegram/Zalo/email)
    raise NotImplementedError


@router.post("/telegram")
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


@router.post("/zalo")
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
