# Module: notifications

**Path:** `packages/notifications`
**Role:** Pluggable notification channels for HITL approval gates (blueprint approval, content approval). Concurrent fan-out to all registered channels.

## Public interface

- `NotificationDispatcher` — concurrent fan-out via `asyncio.gather()` (`dispatcher.py`)
- `ApprovalEvent` — dataclass: run_id, teacher_id, gate_type, summary, approve_url, artifacts_count, judge_score, expires_in_hours (`base.py`)
- `NotificationChannel` — Protocol: `name`, `send()`, `is_available()` (`base.py`)
- `build_dispatcher(stream_manager=None)` → NotificationDispatcher with SSE + Telegram channels (`registry.py`)

## Internal structure

- `channels/sse.py` — `SSEChannel`: pushes to existing SSE stream manager
- `channels/telegram.py` — `TelegramChannel`: httpx-based Telegram Bot API (Markdown formatting)
- `channels/email.py` — `EmailChannel`: stub (`is_available()` always returns `False`)

## Depends on

- **None** (leaf package)
- external: `httpx>=0.27.0`, `pydantic-settings>=2.14.2`

## Used by

- **`gateway`** — at HITL gate nodes (`teaching_pack_completion.py`, `main.py`)

## Data & side effects

- Network calls: Telegram Bot API (outbound, httpx), SSE stream push

---

_Traced from source on 2026-07-10. Files examined: all 11 files. EmailChannel is a stub — needs configuration to enable._
