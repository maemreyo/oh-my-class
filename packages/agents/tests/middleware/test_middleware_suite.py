"""Integration tests for the full middleware suite — ordering and pass-through."""

from typing import Any

from packages.agents.middleware import ORDERED_MIDDLEWARE_LIST
from packages.agents.middleware.base import MiddlewareState
from packages.agents.middleware.context.dynamic_context import DynamicContextMiddleware
from packages.agents.middleware.context.skill_activation import SkillActivationMiddleware
from packages.agents.middleware.registry import (
    GATE_LAYER_MIDDLEWARE,
    GENERATION_CONTEXT_MIDDLEWARE,
    QUALITY_GATE_CONSOLIDATED_MIDDLEWARE,
    RUN_ENTRY_MIDDLEWARE,
)
from packages.agents.middleware.safety.teacher_audit_log import TeacherAuditLogMiddleware
from packages.agents.middleware.terminal.clarification import ClarificationMiddleware


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


class TestMiddlewareList:
    def test_ordered_list_has_23_items(self):
        assert len(ORDERED_MIDDLEWARE_LIST) == 23

    def test_order_is_correct(self):
        orders = [m.order for m in ORDERED_MIDDLEWARE_LIST]
        assert orders == list(range(1, 24))

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

    def test_clarification_is_last(self):
        assert ORDERED_MIDDLEWARE_LIST[-1] is ClarificationMiddleware
        assert ClarificationMiddleware.order == len(ORDERED_MIDDLEWARE_LIST)
