"""Integration tests for the full middleware suite — ordering and pass-through."""

from typing import Any, cast

import pytest

from packages.agents.middleware import ORDERED_MIDDLEWARE_LIST
from packages.agents.middleware.base import MiddlewareContext
from packages.agents.middleware.context.deferred_tool_filter import DeferredToolFilterMiddleware
from packages.agents.middleware.context.dynamic_context import DynamicContextMiddleware
from packages.agents.middleware.context.summarization import SummarizationMiddleware
from packages.agents.middleware.context.skill_activation import SkillActivationMiddleware
from packages.agents.middleware.context.todo_list import TodoListMiddleware
from packages.agents.middleware.context.view_image import ViewImageMiddleware
from packages.agents.middleware.dangling_tool_call import DanglingToolCallMiddleware
from packages.agents.middleware.quality.subagent_limit import SubagentLimitMiddleware
from packages.agents.middleware.registry import (
    GATE_LAYER_MIDDLEWARE,
    GENERATION_CONTEXT_MIDDLEWARE,
    PARKED_REACT_MIDDLEWARE,
    QUALITY_GATE_CONSOLIDATED_MIDDLEWARE,
    RUN_ENTRY_MIDDLEWARE,
)
from packages.agents.middleware.safety.dangling_tool_call import DanglingToolCallMiddleware
from packages.agents.middleware.safety.loop_detection import LoopDetectionMiddleware
from packages.agents.middleware.safety.teacher_audit_log import TeacherAuditLogMiddleware
from packages.agents.middleware.safety.tool_error_handling import ToolErrorHandlingMiddleware
from packages.agents.middleware.terminal.clarification import ClarificationMiddleware
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

    def test_run_entry_group_has_expected_layers(self):
        names = [middleware.name for middleware in RUN_ENTRY_MIDDLEWARE]

        assert names == [
            "input_sanitization",
            "uploads",
            "thread_data",
            "title",
            "memory",
            "token_budget",
        ]

    def test_generation_context_only_targets_planner_and_content_creator(self):
        assert set(GENERATION_CONTEXT_MIDDLEWARE) == {"planner", "content_creator"}
        assert GENERATION_CONTEXT_MIDDLEWARE["planner"] == (
            DynamicContextMiddleware,
            SkillActivationMiddleware,
        )
        assert GENERATION_CONTEXT_MIDDLEWARE["content_creator"] == (
            DynamicContextMiddleware,
            SkillActivationMiddleware,
        )

    def test_gate_layer_group_has_audit_and_clarification(self):
        assert GATE_LAYER_MIDDLEWARE == (TeacherAuditLogMiddleware, ClarificationMiddleware)

    def test_quality_layers_are_consolidated_into_quality_gate(self):
        names = {middleware.name for middleware in QUALITY_GATE_CONSOLIDATED_MIDDLEWARE}

        assert names == {
            "curriculum_alignment",
            "readability_level",
            "pedagogical_quality",
            "bias_detection",
            "artifact_coherence",
            "learning_objective_alignment",
        }

    def test_react_only_middleware_are_parked_not_active(self):
        parked = set(PARKED_REACT_MIDDLEWARE)

        assert parked == {
            DanglingToolCallMiddleware,
            ToolErrorHandlingMiddleware,
            LoopDetectionMiddleware,
            SubagentLimitMiddleware,
            DeferredToolFilterMiddleware,
            SummarizationMiddleware,
            TodoListMiddleware,
            ViewImageMiddleware,
        }
        assert all(PARKED_REACT_MIDDLEWARE[middleware] for middleware in parked)


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
