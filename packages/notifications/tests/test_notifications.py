"""Tests for notification system — J4 pluggable channels."""
from __future__ import annotations
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def make_event(**overrides) -> dict:
    from packages.notifications.base import ApprovalEvent
    defaults = dict(
        run_id="run-001",
        teacher_id="t-001",
        gate_type="content_approval",
        summary="3 artifacts ready for review",
        approve_url="https://app/runs/run-001",
        artifacts_count=3,
        judge_score=8.5,
    )
    defaults.update(overrides)
    return ApprovalEvent(**defaults)


class TestApprovalEvent:
    def test_event_has_required_fields(self):
        from packages.notifications.base import ApprovalEvent
        event = ApprovalEvent(
            run_id="r1", teacher_id="t1", gate_type="blueprint_approval",
            summary="Blueprint ready", approve_url="https://app/r1",
        )
        assert event.run_id == "r1"
        assert event.expires_in_hours == 24  # default

    def test_event_judge_score_optional(self):
        from packages.notifications.base import ApprovalEvent
        event = ApprovalEvent(
            run_id="r1", teacher_id="t1", gate_type="blueprint_approval",
            summary="Ready", approve_url="https://app/r1",
        )
        assert event.judge_score is None


class TestNotificationChannelProtocol:
    def test_sse_channel_satisfies_protocol(self):
        from packages.notifications.base import NotificationChannel
        from packages.notifications.channels.sse import SSEChannel
        ch = SSEChannel()
        assert isinstance(ch, NotificationChannel)

    def test_telegram_channel_satisfies_protocol(self):
        from packages.notifications.base import NotificationChannel
        from packages.notifications.channels.telegram import TelegramChannel
        ch = TelegramChannel()
        assert isinstance(ch, NotificationChannel)

    def test_email_channel_satisfies_protocol(self):
        from packages.notifications.base import NotificationChannel
        from packages.notifications.channels.email import EmailChannel
        ch = EmailChannel()
        assert isinstance(ch, NotificationChannel)


class TestSSEChannel:
    @pytest.mark.asyncio
    async def test_always_available(self):
        from packages.notifications.channels.sse import SSEChannel
        ch = SSEChannel()
        assert await ch.is_available() is True

    @pytest.mark.asyncio
    async def test_send_returns_true(self):
        from packages.notifications.channels.sse import SSEChannel
        ch = SSEChannel()
        result = await ch.send(make_event())
        assert result is True

    @pytest.mark.asyncio
    async def test_publishes_to_stream_when_injected(self):
        from packages.notifications.channels.sse import SSEChannel
        mock_stream = AsyncMock()
        ch = SSEChannel(stream_manager=mock_stream)
        event = make_event()
        await ch.send(event)
        mock_stream.publish.assert_called_once()
        call_args = mock_stream.publish.call_args
        assert call_args[0][0] == event.run_id

    @pytest.mark.asyncio
    async def test_no_stream_does_not_raise(self):
        from packages.notifications.channels.sse import SSEChannel
        ch = SSEChannel(stream_manager=None)
        result = await ch.send(make_event())
        assert result is True


class TestTelegramChannel:
    @pytest.mark.asyncio
    async def test_unavailable_when_no_token(self):
        from packages.notifications.channels.telegram import TelegramChannel, TelegramConfig
        ch = TelegramChannel(TelegramConfig(bot_token="", chat_id=""))
        assert await ch.is_available() is False

    @pytest.mark.asyncio
    async def test_available_when_configured(self):
        from packages.notifications.channels.telegram import TelegramChannel, TelegramConfig
        ch = TelegramChannel(TelegramConfig(bot_token="abc", chat_id="123"))
        assert await ch.is_available() is True

    @pytest.mark.asyncio
    async def test_send_returns_false_when_unavailable(self):
        from packages.notifications.channels.telegram import TelegramChannel, TelegramConfig
        ch = TelegramChannel(TelegramConfig(bot_token="", chat_id=""))
        result = await ch.send(make_event())
        assert result is False

    def test_format_includes_gate_type(self):
        from packages.notifications.channels.telegram import TelegramChannel, TelegramConfig
        ch = TelegramChannel(TelegramConfig(bot_token="x", chat_id="y"))
        event = make_event(gate_type="content_approval")
        msg = ch._format(event)
        assert "content_approval" in msg

    def test_format_includes_run_id(self):
        from packages.notifications.channels.telegram import TelegramChannel, TelegramConfig
        ch = TelegramChannel(TelegramConfig(bot_token="x", chat_id="y"))
        event = make_event(run_id="run-xyz")
        msg = ch._format(event)
        assert "run-xyz" in msg

    def test_format_includes_approve_url(self):
        from packages.notifications.channels.telegram import TelegramChannel, TelegramConfig
        ch = TelegramChannel(TelegramConfig(bot_token="x", chat_id="y"))
        event = make_event(approve_url="https://app/runs/r1")
        msg = ch._format(event)
        assert "https://app/runs/r1" in msg

    def test_format_includes_judge_score_when_present(self):
        from packages.notifications.channels.telegram import TelegramChannel, TelegramConfig
        ch = TelegramChannel(TelegramConfig(bot_token="x", chat_id="y"))
        event = make_event(judge_score=8.5)
        msg = ch._format(event)
        assert "8.5" in msg

    def test_format_excludes_score_line_when_none(self):
        from packages.notifications.channels.telegram import TelegramChannel, TelegramConfig
        ch = TelegramChannel(TelegramConfig(bot_token="x", chat_id="y"))
        event = make_event(judge_score=None)
        msg = ch._format(event)
        assert "Judge score" not in msg

    @pytest.mark.asyncio
    async def test_send_calls_telegram_api(self):
        from packages.notifications.channels.telegram import TelegramChannel, TelegramConfig
        ch = TelegramChannel(TelegramConfig(bot_token="test-token", chat_id="123"))
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch("packages.notifications.channels.telegram.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            result = await ch.send(make_event())
        assert result is True


class TestEmailChannel:
    @pytest.mark.asyncio
    async def test_always_unavailable(self):
        from packages.notifications.channels.email import EmailChannel
        ch = EmailChannel()
        assert await ch.is_available() is False

    @pytest.mark.asyncio
    async def test_send_returns_false(self):
        from packages.notifications.channels.email import EmailChannel
        ch = EmailChannel()
        result = await ch.send(make_event())
        assert result is False


class TestNotificationDispatcher:
    @pytest.mark.asyncio
    async def test_sends_to_available_channels(self):
        from packages.notifications.dispatcher import NotificationDispatcher
        from packages.notifications.channels.sse import SSEChannel
        from packages.notifications.channels.email import EmailChannel
        dispatcher = NotificationDispatcher([SSEChannel(), EmailChannel()])
        results = await dispatcher.notify(make_event())
        assert "sse" in results
        assert "email" not in results  # unavailable — skipped

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_unavailable(self):
        from packages.notifications.dispatcher import NotificationDispatcher
        from packages.notifications.channels.email import EmailChannel
        dispatcher = NotificationDispatcher([EmailChannel()])
        results = await dispatcher.notify(make_event())
        assert results == {}

    @pytest.mark.asyncio
    async def test_concurrent_send(self):
        from packages.notifications.dispatcher import NotificationDispatcher
        from packages.notifications.channels.sse import SSEChannel
        ch1 = SSEChannel()
        ch2 = SSEChannel()
        ch2.name = "sse2"
        dispatcher = NotificationDispatcher([ch1, ch2])
        results = await dispatcher.notify(make_event())
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_channel_error_does_not_crash_others(self):
        from packages.notifications.dispatcher import NotificationDispatcher
        from packages.notifications.channels.sse import SSEChannel
        broken_ch = MagicMock()
        broken_ch.name = "broken"
        broken_ch.is_available = AsyncMock(side_effect=Exception("boom"))
        good_ch = SSEChannel()
        dispatcher = NotificationDispatcher([broken_ch, good_ch])
        results = await dispatcher.notify(make_event())
        assert "sse" in results


class TestRegistry:
    def test_build_dispatcher_returns_dispatcher(self):
        from packages.notifications.registry import build_dispatcher
        from packages.notifications.dispatcher import NotificationDispatcher
        dispatcher = build_dispatcher()
        assert isinstance(dispatcher, NotificationDispatcher)

    def test_dispatcher_has_channels(self):
        from packages.notifications.registry import build_dispatcher
        dispatcher = build_dispatcher()
        assert len(dispatcher.channels) >= 1  # at least SSE
