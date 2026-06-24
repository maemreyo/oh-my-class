---
title: "Notification System: J4 Pattern — Pluggable Channels, SSE + Telegram MVP"
status: ready
labels: [architecture, notifications, hitl]
created: 2026-06-24
priority: p1
---

## What to build

Pluggable `NotificationChannel` Protocol — ship SSE (already wired) + Telegram (free, ~50 lines). Email deferred. New channels add by creating one file, zero core changes.

**Design decisions:**
- **J4**: Protocol-based pluggable system
- **No budget**: Telegram free (no SMTP/SendGrid needed)
- **Dev as first user**: SSE sufficient when at dashboard; Telegram for async
- **Vietnamese context**: Telegram > Email for teacher notifications

## File Structure

```
packages/notifications/
├── __init__.py
├── base.py               # NotificationChannel Protocol + ApprovalEvent
├── registry.py           # ENABLED_CHANNELS list
├── dispatcher.py         # NotificationDispatcher — fan-out to all channels
├── channels/
│   ├── __init__.py
│   ├── sse.py            # SSEChannel — triggers existing ApprovalModal
│   ├── telegram.py       # TelegramChannel — free bot (~50 lines)
│   └── email.py          # EmailChannel — stub (add when needed)
└── tests/
    ├── test_dispatcher.py
    └── test_telegram.py
```

## Implementation Spec

### `notifications/base.py`

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class ApprovalEvent:
    run_id: str
    teacher_id: str
    gate_type: str          # "blueprint_approval" | "content_approval"
    summary: str            # human-readable summary of what needs approval
    approve_url: str        # deep link into dashboard
    artifacts_count: int = 0
    judge_score: float | None = None
    expires_in_hours: int = 24


@runtime_checkable
class NotificationChannel(Protocol):
    """Every channel implements exactly this interface."""
    name: str

    async def send(self, event: ApprovalEvent) -> bool:
        """Send notification. Returns True on success."""
        ...

    async def is_available(self) -> bool:
        """Check if channel is configured and reachable."""
        ...
```

### `notifications/channels/telegram.py`

```python
"""Telegram bot notification channel. Free, no SDK needed."""
from __future__ import annotations
import httpx
from packages.notifications.base import ApprovalEvent, NotificationChannel
from pydantic_settings import BaseSettings, SettingsConfigDict


class TelegramConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TELEGRAM_", env_file=".env", extra="ignore")
    bot_token: str = ""
    chat_id: str = ""


class TelegramChannel:
    name = "telegram"

    def __init__(self, config: TelegramConfig | None = None):
        self._config = config or TelegramConfig()

    async def is_available(self) -> bool:
        return bool(self._config.bot_token and self._config.chat_id)

    async def send(self, event: ApprovalEvent) -> bool:
        if not await self.is_available():
            return False

        text = self._format(event)
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{self._config.bot_token}/sendMessage",
                json={
                    "chat_id": self._config.chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                },
                timeout=10.0,
            )
        return resp.status_code == 200

    def _format(self, event: ApprovalEvent) -> str:
        score_line = f"Judge score: {event.judge_score:.1f}/10\n" if event.judge_score else ""
        return (
            f"📋 *Approval Required*\n\n"
            f"{event.summary}\n\n"
            f"{score_line}"
            f"Gate: `{event.gate_type}`\n"
            f"Run: `{event.run_id}`\n\n"
            f"[Open Dashboard]({event.approve_url})\n\n"
            f"⏰ Expires in {event.expires_in_hours}h"
        )
```

### `notifications/channels/sse.py`

```python
"""SSE channel — pushes event to existing RunStream (already implemented)."""
from __future__ import annotations
from packages.notifications.base import ApprovalEvent


class SSEChannel:
    """Triggers ApprovalModal via existing SSE infrastructure.

    The frontend's useRunStatus() hook listens for 'interrupt' events.
    This channel publishes the event to the run's SSE stream.
    """
    name = "sse"

    def __init__(self, stream_manager=None):
        self._stream = stream_manager  # injected — avoids circular import

    async def is_available(self) -> bool:
        return True  # always available

    async def send(self, event: ApprovalEvent) -> bool:
        if self._stream:
            await self._stream.publish(event.run_id, {
                "type": "interrupt",
                "gate": event.gate_type,
                "run_id": event.run_id,
                "summary": event.summary,
            })
        return True
```

### `notifications/channels/email.py`

```python
"""Email channel stub — wire up when Resend/SMTP ready."""
from __future__ import annotations
from packages.notifications.base import ApprovalEvent


class EmailChannel:
    name = "email"

    async def is_available(self) -> bool:
        return False  # disabled until configured

    async def send(self, event: ApprovalEvent) -> bool:
        # TODO: implement with Resend free tier when needed
        return False
```

### `notifications/dispatcher.py`

```python
"""Fan-out dispatcher — sends to all available channels."""
from __future__ import annotations
import asyncio
import logging
from packages.notifications.base import ApprovalEvent, NotificationChannel

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    def __init__(self, channels: list[NotificationChannel]):
        self.channels = channels

    async def notify(self, event: ApprovalEvent) -> dict[str, bool]:
        """Send to all available channels concurrently."""
        tasks = {
            ch.name: ch.send(event)
            for ch in self.channels
            if await ch.is_available()
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        return {
            name: (result is True)
            for name, result in zip(tasks.keys(), results)
        }
```

### `notifications/registry.py`

```python
"""Channel registry — add new channels here, zero other changes needed."""
from packages.notifications.channels.sse import SSEChannel
from packages.notifications.channels.telegram import TelegramChannel
from packages.notifications.channels.email import EmailChannel
from packages.notifications.dispatcher import NotificationDispatcher


def build_dispatcher(stream_manager=None) -> NotificationDispatcher:
    """Build dispatcher with all enabled channels."""
    return NotificationDispatcher(channels=[
        SSEChannel(stream_manager=stream_manager),
        TelegramChannel(),
        # EmailChannel(),     # uncomment when Resend configured
    ])
```

## Integration with gate_02

```python
# packages/agents/gates/gate_02_content.py

async def gate_02_content_approval(state: OhMyClassState) -> dict:
    dispatcher = build_dispatcher()
    await dispatcher.notify(ApprovalEvent(
        run_id=state["run_id"],
        teacher_id=state["teacher_id"],
        gate_type="content_approval",
        summary=f"{len(state['artifacts'])} artifacts ready for review",
        approve_url=f"{settings.app_url}/runs/{state['run_id']}",
        judge_score=state.get("judge_score"),
    ))

    response = interrupt({...})
    ...
```

## Tests

```python
def test_telegram_formats_message_correctly():
    ch = TelegramChannel(TelegramConfig(bot_token="x", chat_id="y"))
    event = ApprovalEvent(run_id="r1", teacher_id="t1",
                          gate_type="content_approval",
                          summary="3 artifacts ready",
                          approve_url="https://app/runs/r1")
    msg = ch._format(event)
    assert "content_approval" in msg
    assert "r1" in msg
    assert "https://app/runs/r1" in msg

async def test_dispatcher_skips_unavailable_channels():
    sse = SSEChannel()
    email = EmailChannel()   # always unavailable
    dispatcher = NotificationDispatcher([sse, email])
    results = await dispatcher.notify(ApprovalEvent(...))
    assert "sse" in results
    assert "email" not in results   # skipped, not available

async def test_telegram_skips_when_no_token():
    ch = TelegramChannel(TelegramConfig(bot_token="", chat_id=""))
    assert not await ch.is_available()
```

## Acceptance Criteria

- [ ] `NotificationChannel` Protocol defined in `base.py`
- [ ] `SSEChannel` integrates with existing run stream (no new SSE infrastructure)
- [ ] `TelegramChannel` sends approval messages via httpx (no SDK)
- [ ] `EmailChannel` is a stub — `is_available()` returns False until configured
- [ ] `NotificationDispatcher` fans out concurrently, skips unavailable channels
- [ ] Adding a new channel = create one file + add to `registry.py`
- [ ] `.env.example` includes `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`

## Dependencies

- Blocked by: nothing (standalone module)
- Blocks: `hitl-gate-wrapper` (gate_02 needs dispatcher)
- Priority: p1
