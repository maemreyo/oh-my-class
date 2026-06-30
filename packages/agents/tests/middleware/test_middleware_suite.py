"""Integration tests for the full middleware suite — ordering and pass-through."""

from typing import Any, cast

import pytest

from packages.agents.middleware import ORDERED_MIDDLEWARE_LIST
from packages.agents.middleware.base import MiddlewareContext
from packages.agents.middleware.dangling_tool_call import DanglingToolCallMiddleware
from packages.agents.middleware.summarization import SummarizationMiddleware
from packages.agents.state import OhMyClassState


def make_state(**overrides: Any) -> OhMyClassState:
    base: dict[str, Any] = {
        "raw_request": "Teach photosynthesis",
        "teacher_id": "t-001",
        "class_info": {"grade": 5, "subject": "science"},
        "run_id": "run-001",
        "blueprint_approved": False,
        "quality_passed": False,
        "teacher_approved": False,
        "revision_count": 0,
        "artifact_types": [],
        "theme": "default",
        "artifacts": [],
        "export_formats": [],
        "exported_files": [],
        "current_step": 1,
        "tokens_used": 0,
        "cost_usd": 0.0,
        "research_policy": "basic",
    }
    return cast("OhMyClassState", {**base, **overrides})


class TestMiddlewareList:
    def test_ordered_list_has_31_items(self):
        assert len(ORDERED_MIDDLEWARE_LIST) == 31

    def test_order_is_correct(self):
        orders = [m.order for m in ORDERED_MIDDLEWARE_LIST]
        assert orders == list(range(1, 32))

    def test_all_items_are_classes(self):
        for m in ORDERED_MIDDLEWARE_LIST:
            assert isinstance(m, type)

    def test_names_are_unique(self):
        names = [m.name for m in ORDERED_MIDDLEWARE_LIST]
        assert len(names) == len(set(names))


class TestDanglingToolCall:
    @pytest.mark.asyncio
    async def test_pass_through_before_model(self):
        middleware = DanglingToolCallMiddleware()
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state()

        result = await middleware.before_model(state, context)
        assert result == state

    @pytest.mark.asyncio
    async def test_pass_through_after_model(self):
        middleware = DanglingToolCallMiddleware()
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state()

        result = await middleware.after_model(state, context)
        assert result == state

    @pytest.mark.asyncio
    async def test_clears_pending_tool_calls(self):
        middleware = DanglingToolCallMiddleware()
        context = MiddlewareContext(
            agent_name="test",
            step=1,
            run_id="r1",
            metadata={"pending_tool_calls": ["call-1", "call-2"]},
        )
        state = make_state()

        await middleware.before_model(state, context)
        assert context.metadata["pending_tool_calls"] == []

    def test_name_and_order(self):
        assert DanglingToolCallMiddleware.name == "dangling_tool_call"
        assert DanglingToolCallMiddleware.order == 6


class TestSummarization:
    @pytest.mark.asyncio
    async def test_pass_through_below_threshold(self):
        middleware = SummarizationMiddleware(threshold_tokens=80_000)
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state(tokens_used=1000)

        result = await middleware.before_model(state, context)
        assert result == state
        assert not context.metadata.get("summarization_triggered")

    @pytest.mark.asyncio
    async def test_triggers_above_threshold(self):
        middleware = SummarizationMiddleware(threshold_tokens=1000)
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state(tokens_used=5000)

        await middleware.before_model(state, context)
        assert context.metadata.get("summarization_triggered") is True

    @pytest.mark.asyncio
    async def test_after_model_noop(self):
        middleware = SummarizationMiddleware()
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state()

        result = await middleware.after_model(state, context)
        assert result == state

    def test_name_and_order(self):
        assert SummarizationMiddleware.name == "summarization"
        assert SummarizationMiddleware.order == 15
