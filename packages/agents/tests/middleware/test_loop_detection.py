"""Tests for loop_detection middleware."""

from typing import Any, cast

import pytest

from packages.agents.middleware.base import MiddlewareContext
from packages.agents.middleware.loop_detection import LoopDetectedError, LoopDetectionMiddleware
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


class TestLoopDetection:
    @pytest.mark.asyncio
    async def test_allows_different_states(self):
        middleware = LoopDetectionMiddleware(threshold=3)
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")

        # Use fields that ARE hashed: artifacts changes each iteration
        for i in range(5):
            state = make_state(artifacts=[{"id": i}])
            await middleware.before_model(state, context)
            await middleware.after_model(state, context)

    @pytest.mark.asyncio
    async def test_breaks_after_threshold(self):
        middleware = LoopDetectionMiddleware(threshold=3)
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")

        state = make_state()
        for _ in range(3):
            await middleware.before_model(state, context)
            await middleware.after_model(state, context)

        with pytest.raises(LoopDetectedError):
            await middleware.before_model(state, context)

    @pytest.mark.asyncio
    async def test_does_not_break_before_threshold(self):
        middleware = LoopDetectionMiddleware(threshold=5)
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")

        state = make_state()
        for _ in range(4):
            await middleware.before_model(state, context)
            await middleware.after_model(state, context)

        # 4 cycles — should not raise yet
        result = await middleware.before_model(state, context)
        assert result == state

    @pytest.mark.asyncio
    async def test_threshold_one(self):
        middleware = LoopDetectionMiddleware(threshold=1)
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")

        state = make_state()
        await middleware.before_model(state, context)
        await middleware.after_model(state, context)

        with pytest.raises(LoopDetectedError):
            await middleware.before_model(state, context)

    @pytest.mark.asyncio
    async def test_resets_on_different_state(self):
        middleware = LoopDetectionMiddleware(threshold=3)
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")

        # Use artifacts field (it's in the hash)
        state_a = make_state(artifacts=[{"id": "a"}])
        state_b = make_state(artifacts=[{"id": "b"}])

        for _ in range(3):
            await middleware.before_model(state_a, context)
            await middleware.after_model(state_a, context)

        # Different hashed state should not raise (pattern broken by state_b)
        await middleware.before_model(state_b, context)

    @pytest.mark.asyncio
    async def test_sliding_window_trims(self):
        middleware = LoopDetectionMiddleware(threshold=3)
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")

        # Alternate between two distinct states so the loop never trips,
        # but we still accumulate enough entries to trigger the trim.
        for i in range(10):
            state = make_state(artifacts=[{"id": i % 2}])
            await middleware.before_model(state, context)
            await middleware.after_model(state, context)

        # History should be bounded to threshold * 2
        assert len(middleware._hash_history) <= middleware.threshold * 2

    def test_name_and_order(self):
        assert LoopDetectionMiddleware.name == "loop_detection"
        assert LoopDetectionMiddleware.order == 11
