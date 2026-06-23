"""Tests for layer5_human — InterruptHandler."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.quality.layer5_human.interrupt_handler import (
    InterruptConfig,
    InterruptHandler,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_langgraph_types_mock(interrupt_return_value: dict) -> MagicMock:
    mock_module = MagicMock()
    mock_module.interrupt = MagicMock(return_value=interrupt_return_value)
    return mock_module


# ── InterruptHandler.create_gate ──────────────────────────────────────────────

class TestCreateGate:
    @pytest.mark.asyncio
    async def test_returns_approve_response(self):
        mock_types = _make_langgraph_types_mock({"action": "approve"})
        with patch.dict(sys.modules, {"langgraph.types": mock_types}):
            handler = InterruptHandler()
            result = await handler.create_gate("blueprint_approval", {"lesson_plan": {"topic": "T"}})

        assert result["action"] == "approve"

    @pytest.mark.asyncio
    async def test_returns_reject_response_with_feedback(self):
        mock_types = _make_langgraph_types_mock({"action": "reject", "feedback": "Too short"})
        with patch.dict(sys.modules, {"langgraph.types": mock_types}):
            handler = InterruptHandler()
            result = await handler.create_gate("blueprint_approval", {})

        assert result["action"] == "reject"
        assert result["feedback"] == "Too short"

    @pytest.mark.asyncio
    async def test_blueprint_gate_includes_lesson_plan(self):
        mock_types = _make_langgraph_types_mock({"action": "approve"})
        with patch.dict(sys.modules, {"langgraph.types": mock_types}):
            handler = InterruptHandler()
            state = {"lesson_plan": {"topic": "Math"}}
            await handler.create_gate("blueprint_approval", state)

        call_args = mock_types.interrupt.call_args[0][0]
        assert call_args["gate"] == "blueprint_approval"
        assert call_args["lesson_plan"] == {"topic": "Math"}

    @pytest.mark.asyncio
    async def test_content_gate_includes_artifacts_and_scores(self):
        mock_types = _make_langgraph_types_mock({"action": "approve"})
        with patch.dict(sys.modules, {"langgraph.types": mock_types}):
            handler = InterruptHandler()
            state = {
                "artifacts": [{"type": "lesson"}],
                "quality_scores": {"overall_score": 8.0},
            }
            await handler.create_gate("content_approval", state)

        call_args = mock_types.interrupt.call_args[0][0]
        assert call_args["gate"] == "content_approval"
        assert call_args["artifacts"] == [{"type": "lesson"}]
        assert call_args["quality_scores"] == {"overall_score": 8.0}

    @pytest.mark.asyncio
    async def test_no_webhook_when_url_not_set(self):
        mock_types = _make_langgraph_types_mock({"action": "approve"})
        with patch.dict(sys.modules, {"langgraph.types": mock_types}):
            handler = InterruptHandler(InterruptConfig(webhook_url=None))
            # Should not raise even without webhook
            result = await handler.create_gate("blueprint_approval", {})

        assert result["action"] == "approve"

    @pytest.mark.asyncio
    async def test_sends_webhook_when_url_configured(self):
        mock_types = _make_langgraph_types_mock({"action": "approve"})

        mock_httpx = MagicMock()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock()
        mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch.dict(sys.modules, {"langgraph.types": mock_types, "httpx": mock_httpx}):
            handler = InterruptHandler(InterruptConfig(webhook_url="https://hook.example.com"))
            await handler.create_gate("blueprint_approval", {})

        mock_client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_includes_actions_in_gate_data(self):
        mock_types = _make_langgraph_types_mock({"action": "approve"})
        with patch.dict(sys.modules, {"langgraph.types": mock_types}):
            handler = InterruptHandler()
            await handler.create_gate("blueprint_approval", {})

        call_args = mock_types.interrupt.call_args[0][0]
        assert "actions" in call_args
        assert "approve" in call_args["actions"]


# ── InterruptHandler.handle_timeout ──────────────────────────────────────────

class TestHandleTimeout:
    @pytest.mark.asyncio
    async def test_returns_escalation_response(self):
        handler = InterruptHandler()
        result = await handler.handle_timeout("blueprint_approval")
        assert result["action"] == "escalate"

    @pytest.mark.asyncio
    async def test_auto_approved_is_true(self):
        handler = InterruptHandler()
        result = await handler.handle_timeout("content_approval")
        assert result["auto_approved"] is True

    @pytest.mark.asyncio
    async def test_reason_includes_gate_type(self):
        handler = InterruptHandler()
        result = await handler.handle_timeout("blueprint_approval")
        assert "blueprint_approval" in result["reason"]

    @pytest.mark.asyncio
    async def test_reason_includes_timeout_hours(self):
        handler = InterruptHandler(InterruptConfig(timeout_hours=48))
        result = await handler.handle_timeout("content_approval")
        assert "48" in result["reason"]

    @pytest.mark.asyncio
    async def test_sends_timeout_webhook_when_configured(self):
        mock_httpx = MagicMock()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock()
        mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch.dict(sys.modules, {"httpx": mock_httpx}):
            handler = InterruptHandler(InterruptConfig(webhook_url="https://hook.example.com"))
            await handler.handle_timeout("blueprint_approval")

        mock_client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_webhook_when_url_not_set(self):
        handler = InterruptHandler(InterruptConfig(webhook_url=None))
        result = await handler.handle_timeout("blueprint_approval")
        # Should not raise
        assert result["action"] == "escalate"
