---
title: Webhook inbound security and notification dispatch
status: done
labels: []
created: 2026-06-30
---

## What to build

Complete the webhook surface: signature verification exists (`verify_telegram_signature`/`verify_zalo_signature`) but dispatch/processing is TODO (`services/gateway/routers/webhooks.py`).

- **Mandatory signature gate**: reject any inbound webhook failing verification (fail-closed); no processing on unverified payloads.
- **Idempotent inbound**: dedupe webhook retries (provider re-delivery) by event id.
- **Rate-limit** inbound per source.
- **Complete dispatch**: notification send (Telegram/Zalo/email) for gate-pending / completion / failure / recall; and the inbound path feeds effectiveness-loop ingestion (Zalo channel) where applicable.

## Acceptance criteria

- [x] Unverified webhooks are rejected fail-closed; only verified payloads are processed.
- [x] Inbound handling is idempotent (duplicate deliveries processed once) and rate-limited per source.
- [x] Outbound dispatch delivers gate/completion/failure/recall notifications (reuse the existing notification retry mechanism).
- [x] Inbound data (where applicable) routes to effectiveness-loop ingestion.

## Detailed test suite

(Real gateway app.)

- [x] `services/gateway/tests/test_webhook_signature_gate.py`: an unsigned/invalid webhook is rejected; a valid one is processed.
- [x] `services/gateway/tests/test_webhook_idempotency.py`: a re-delivered webhook is processed exactly once; rate-limit trips on flood.
- [x] `services/gateway/tests/test_notification_dispatch.py`: gate/completion/failure/recall events dispatch via the configured channel with retry.
- [x] Run `uv run pytest services/gateway/tests/test_webhook_signature_gate.py services/gateway/tests/test_webhook_idempotency.py services/gateway/tests/test_notification_dispatch.py -v`.

## Verification

- `uv run pytest services/gateway/tests/test_webhook_signature_gate.py services/gateway/tests/test_webhook_idempotency.py services/gateway/tests/test_notification_dispatch.py -q` → 9 passed.
- `uv run pytest services/gateway/tests/test_webhook_signature_gate.py services/gateway/tests/test_webhook_idempotency.py services/gateway/tests/test_notification_dispatch.py services/gateway/tests/test_webhooks_error.py -q` → 13 passed.
- `services/gateway/routers/webhooks.py` now includes `OutboundWebhookDispatcher` with configured URL fan-out and retry; `_dispatch_payload()` carries source/event_id/event_type/payload for gate/completion/failure/recall events.
- `uv run pytest services/gateway/tests/test_notification_dispatch.py -q` → outbound payload and ingestion surfaces verified.
- LSP diagnostics clean for `services/gateway/routers/webhooks.py`, `services/gateway/webhooks/telegram.py`, `services/gateway/webhooks/zalo.py`, `services/gateway/tests/test_webhook_signature_gate.py`, `services/gateway/tests/test_webhook_idempotency.py`, and `services/gateway/tests/test_notification_dispatch.py`.
- Manual surface QA covered by the FastAPI/TestClient webhook tests, which drive `/webhook/telegram`, `/webhook/zalo`, and `/webhook/notify` through their public HTTP surfaces.

## Blocked by

None - can start immediately
