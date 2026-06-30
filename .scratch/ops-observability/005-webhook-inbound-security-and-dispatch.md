---
title: Webhook inbound security and notification dispatch
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Complete the webhook surface: signature verification exists (`verify_telegram_signature`/`verify_zalo_signature`) but dispatch/processing is TODO (`services/gateway/routers/webhooks.py`).

- **Mandatory signature gate**: reject any inbound webhook failing verification (fail-closed); no processing on unverified payloads.
- **Idempotent inbound**: dedupe webhook retries (provider re-delivery) by event id.
- **Rate-limit** inbound per source.
- **Complete dispatch**: notification send (Telegram/Zalo/email) for gate-pending / completion / failure / recall; and the inbound path feeds effectiveness-loop ingestion (Zalo channel) where applicable.

## Acceptance criteria

- [ ] Unverified webhooks are rejected fail-closed; only verified payloads are processed.
- [ ] Inbound handling is idempotent (duplicate deliveries processed once) and rate-limited per source.
- [ ] Outbound dispatch delivers gate/completion/failure/recall notifications (reuse the existing notification retry mechanism).
- [ ] Inbound data (where applicable) routes to effectiveness-loop ingestion.

## Detailed test suite

(Real gateway app.)

- [ ] `services/gateway/tests/test_webhook_signature_gate.py`: an unsigned/invalid webhook is rejected; a valid one is processed.
- [ ] `services/gateway/tests/test_webhook_idempotency.py`: a re-delivered webhook is processed exactly once; rate-limit trips on flood.
- [ ] `services/gateway/tests/test_notification_dispatch.py`: gate/completion/failure/recall events dispatch via the configured channel with retry.
- [ ] Run `uv run pytest services/gateway/tests/test_webhook_signature_gate.py services/gateway/tests/test_webhook_idempotency.py services/gateway/tests/test_notification_dispatch.py -v`.

## Blocked by

None - can start immediately
