"""Tests for guardrail middleware."""

from typing import Any

import pytest

from packages.agents.middleware.base import MiddlewareContext, MiddlewareState
from packages.agents.middleware.guardrail import GuardrailMiddleware, GuardrailViolationError


def make_state(**overrides: Any) -> MiddlewareState:
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
    return MiddlewareState(**{**base, **overrides})


class TestGuardrail:
    @pytest.mark.asyncio
    async def test_blocks_email_in_input(self):
        middleware = GuardrailMiddleware()
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state(raw_request="Contact john@example.com for details")

        with pytest.raises(GuardrailViolationError) as exc_info:
            await middleware.before_model(state, context)
        assert "Email" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_blocks_phone_in_input(self):
        middleware = GuardrailMiddleware()
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state(raw_request="Call 555-123-4567 for help")

        with pytest.raises(GuardrailViolationError) as exc_info:
            await middleware.before_model(state, context)
        assert "Phone" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_allows_safe_content(self):
        middleware = GuardrailMiddleware()
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state(raw_request="Teach photosynthesis to grade 5")

        result = await middleware.before_model(state, context)
        assert result == state

    @pytest.mark.asyncio
    async def test_allows_empty_request(self):
        middleware = GuardrailMiddleware()
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state(raw_request="")

        result = await middleware.before_model(state, context)
        assert result == state

    @pytest.mark.asyncio
    async def test_blocks_email_in_output_artifacts(self):
        middleware = GuardrailMiddleware()
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state(artifacts=[{"content": "Contact teacher@school.edu"}])

        with pytest.raises(GuardrailViolationError) as exc_info:
            await middleware.after_model(state, context)
        assert "Email" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_blocks_phone_in_output_artifacts(self):
        middleware = GuardrailMiddleware()
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state(artifacts=[{"content": "Call 555-987-6543"}])

        with pytest.raises(GuardrailViolationError) as exc_info:
            await middleware.after_model(state, context)
        assert "Phone" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_allows_clean_output(self):
        middleware = GuardrailMiddleware()
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state(artifacts=[{"content": "This is a lesson about plants"}])

        result = await middleware.after_model(state, context)
        assert result == state

    @pytest.mark.asyncio
    async def test_empty_artifacts_no_crash(self):
        middleware = GuardrailMiddleware()
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state(artifacts=[])

        result = await middleware.after_model(state, context)
        assert result == state

    def test_name_and_order(self):
        assert GuardrailMiddleware.name == "guardrail"
        assert GuardrailMiddleware.order == 7
