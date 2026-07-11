# Module: notifications

**Path:** `packages/notifications`
**Role:** Pluggable notification dispatcher — sends approval-gate alerts to teachers via SSE (real-time dashboard), Telegram bot, and (stubbed) email. Concurrent fan-out to all registered channels.

## Public interface

```python
# packages/notifications/__init__.py
ApprovalEvent            # dataclass: run_id, teacher_id, gate_type, summary, approve_url, artifacts_count, judge_score, expires_in_hours
NotificationChannel      # Protocol: name, send(), is_available()
NotificationDispatcher   # Fan-out via asyncio.gather()
build_dispatcher(stream_manager=None) → NotificationDispatcher
```

### ApprovalEvent (`base.py`)

```python
@dataclass
class ApprovalEvent:
    run_id: str
    teacher_id: str
    gate_type: str          # "blueprint_approval" | "content_approval"
    summary: str            # human-readable summary
    approve_url: str        # deep link into dashboard
    artifacts_count: int = 0
    judge_score: float | None = None
    expires_in_hours: int = 24
```

### NotificationChannel (`base.py`)

```python
@runtime_checkable
class NotificationChannel(Protocol):
    name: str
    async def send(event: ApprovalEvent) -> bool: ...    # True on success
    async def is_available() -> bool: ...                 # True if configured
```

### NotificationDispatcher (`dispatcher.py`)

```python
class NotificationDispatcher:
    def __init__(self, channels: list[Any]): ...
    async def notify(event: ApprovalEvent) -> dict[str, bool]  # {channel_name: success}
```

Fan-out: checks `is_available()` on each channel, then sends concurrently via `asyncio.gather()` with `return_exceptions=True`.

### build_dispatcher (`registry.py`)

```python
def build_dispatcher(stream_manager=None) -> NotificationDispatcher:
    # Returns dispatcher with [SSEChannel, TelegramChannel]
    # EmailChannel is commented out until configured
```

## Internal structure

```
packages/notifications/
├── __init__.py              # Public API: 4 exports
├── base.py                  # ApprovalEvent dataclass, NotificationChannel Protocol
├── dispatcher.py            # NotificationDispatcher (concurrent fan-out)
├── registry.py              # build_dispatcher() factory
├── channels/
│   ├── __init__.py          # Re-exports SSEChannel, TelegramChannel, EmailChannel
│   ├── sse.py               # SSEChannel — pushes via RunStream
│   ├── telegram.py          # TelegramChannel — Telegram Bot API via httpx
│   └── email.py             # EmailChannel — stub (always returns False)
├── tests/
│   └── test_notifications.py
└── pyproject.toml
```

### Channel implementations

**SSEChannel** (`channels/sse.py`):
- Always available (`is_available() → True`)
- Pushes to `stream_manager.publish(run_id, {...})` if manager injected
- Format: `{"type": "interrupt", "gate": gate_type, "run_id": run_id, "summary": summary}`

**TelegramChannel** (`channels/telegram.py`):
- Available when `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` env vars are set
- Sends via `httpx.AsyncClient` to `https://api.telegram.org/bot{token}/sendMessage`
- Markdown-formatted: approval summary, judge score, gate type, run ID, dashboard link, expiry
- Config: `TelegramConfig(BaseSettings)` with `TELEGRAM_*` env prefix

**EmailChannel** (`channels/email.py`):
- Stub — `is_available()` always returns `False`
- Placeholder for Resend/SMTP integration

## Depends on

_None (leaf node)._

| Target | What | Where cited |
|--------|------|-------------|
| **(none)** | No internal project dependencies | Verified: all imports are from stdlib, httpx, or pydantic_settings |
| `httpx` | HTTP client for Telegram Bot API | `channels/telegram.py:5` (external) |
| `pydantic_settings` | `BaseSettings` for `TelegramConfig` | `channels/telegram.py:6` (external) |

**Phase 3 hypothesis "no outbound imports to other project modules" — CONFIRMED.** The notifications package is a pure leaf node with zero internal dependencies. All channel implementations are self-contained.

## Used by

- **`gateway`** — build_dispatcher, NotificationDispatcher, ApprovalEvent in main.py, teaching_pack_completion.py

| Consumer | What imported | Where |
|----------|---------------|-------|
| **gateway** | `build_dispatcher`, `NotificationDispatcher`, `ApprovalEvent` | `services/gateway/main.py`, `teaching_pack_completion.py` |

## Data & side effects

- **Network:** TelegramChannel makes outbound HTTPS calls to `api.telegram.org`
- **Config:** Reads `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` env vars
- **Async I/O:** Dispatcher uses `asyncio.gather()` for concurrent channel delivery
- **State:** Stateless — no persistent state

## Notes / discrepancies vs existing docs

- **EmailChannel** exists as a stub but is commented out in `registry.py:15`. No Resend/SMTP implementation exists.
- **Zalo notification channel** (mentioned in AGENTS.md §7.5 as "Telegram/Zalo/email") does not exist in code. Only SSE and Telegram are implemented.
- The `pyproject.toml` declares `httpx>=0.27.0` and `pydantic-settings>=2.14.2` as dependencies — no internal packages listed.
- The `channels/__init__.py` re-exports `EmailChannel` even though it's disabled — this means `build_dispatcher()` could theoretically include it if uncommented.

---
_Traced from source on 2026-07-11. Files examined in depth: all 8 source + 1 test file in packages/notifications/. Clean leaf node with zero internal dependencies._
