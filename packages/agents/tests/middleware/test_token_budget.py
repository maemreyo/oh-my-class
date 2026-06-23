"""Tests for token_budget middleware."""

import pytest

from packages.agents.middleware.base import MiddlewareContext
from packages.agents.middleware.token_budget import TokenBudgetExceededError, TokenBudgetMiddleware


def make_state(**overrides):
    base = {
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
    base.update(overrides)
    return base


class TestTokenBudget:
    @pytest.mark.asyncio
    async def test_allows_within_budget(self):
        middleware = TokenBudgetMiddleware(budget=1000)
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state(tokens_used=500)

        result = await middleware.before_model(state, context)
        assert result == state

    @pytest.mark.asyncio
    async def test_blocks_when_exceeded(self):
        middleware = TokenBudgetMiddleware(budget=1000)
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state(tokens_used=1500)

        with pytest.raises(TokenBudgetExceededError):
            await middleware.before_model(state, context)

    @pytest.mark.asyncio
    async def test_blocks_at_exact_budget(self):
        middleware = TokenBudgetMiddleware(budget=1000)
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state(tokens_used=1000)

        with pytest.raises(TokenBudgetExceededError):
            await middleware.before_model(state, context)

    @pytest.mark.asyncio
    async def test_budget_zero_always_blocked(self):
        middleware = TokenBudgetMiddleware(budget=0)
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state(tokens_used=0)

        with pytest.raises(TokenBudgetExceededError):
            await middleware.before_model(state, context)

    @pytest.mark.asyncio
    async def test_after_model_syncs_usage(self):
        middleware = TokenBudgetMiddleware(budget=10_000)
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state(tokens_used=5000)

        await middleware.after_model(state, context)
        assert middleware._used == 5000

    @pytest.mark.asyncio
    async def test_before_model_syncs_from_state(self):
        middleware = TokenBudgetMiddleware(budget=10_000)
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state(tokens_used=300)

        await middleware.before_model(state, context)
        assert middleware._used == 300

    @pytest.mark.asyncio
    async def test_empty_state_no_crash(self):
        middleware = TokenBudgetMiddleware(budget=1000)
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state()  # tokens_used=0

        result = await middleware.before_model(state, context)
        assert result is not None

    def test_name_and_order(self):
        assert TokenBudgetMiddleware.name == "token_budget"
        assert TokenBudgetMiddleware.order == 2
