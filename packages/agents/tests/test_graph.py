"""Tests for graph backbone — graph builder and checkpointer.

langgraph is not available in the pytest environment (no pytest in venv),
so all langgraph-dependent tests use sys.modules injection, same as litellm.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock, patch

import pytest

from packages.agents.checkpointer import get_checkpointer
from packages.agents.graph import (
    route_after_content_review,
    route_after_export,
    route_after_human_review,
    route_after_judge,
    route_after_review,
    route_after_schema,
)

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState

# ── helpers ───────────────────────────────────────────────────────────────────

def make_state(**overrides) -> OhMyClassState:
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
    return cast("OhMyClassState", base)


def _make_langgraph_mocks():
    """Build sys.modules patch entries for langgraph."""
    # Track which nodes were registered
    _nodes: dict[str, Any] = {}

    class _MockStateGraph:
        def __init__(self, state_class):
            pass

        def add_node(self, name, func):
            _nodes[name] = func

        def add_edge(self, src, dst):
            pass

        def add_conditional_edges(self, src, func, mapping):
            pass

        def set_entry_point(self, node):
            pass

        def compile(self, checkpointer=None):
            all_nodes = {"__start__": None, **_nodes, "__end__": None}
            mock_compiled = MagicMock()
            mock_inner_graph = MagicMock()
            mock_inner_graph.nodes = all_nodes
            mock_compiled.get_graph.return_value = mock_inner_graph
            return mock_compiled

    class _MockMemorySaver:
        pass

    mock_graph_module = MagicMock()
    mock_graph_module.StateGraph = _MockStateGraph
    mock_graph_module.END = "__end__"

    mock_memory_module = MagicMock()
    mock_memory_module.MemorySaver = _MockMemorySaver

    mock_types_module = MagicMock()

    return {
        "langgraph": MagicMock(),
        "langgraph.graph": mock_graph_module,
        "langgraph.checkpoint": MagicMock(),
        "langgraph.checkpoint.memory": mock_memory_module,
        "langgraph.types": mock_types_module,
    }, _MockMemorySaver, _nodes


# ── Checkpointer (ValueError — no langgraph needed) ───────────────────────────

class TestCheckpointerErrors:
    def test_unknown_env_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown environment"):
            get_checkpointer("unknown")

    def test_error_message_lists_valid_envs(self):
        try:
            get_checkpointer("invalid")
        except ValueError as e:
            assert "development" in str(e)
            assert "staging" in str(e)
            assert "production" in str(e)

    def test_production_raises_without_connection_string(self):
        mocks, _, _ = _make_langgraph_mocks()
        # Add postgres mock (raises AttributeError for from_conn_string)
        mock_postgres = MagicMock()
        mock_postgres.PostgresSaver.from_conn_string.side_effect = None
        mocks["langgraph.checkpoint.postgres"] = mock_postgres

        with patch.dict(sys.modules, mocks), pytest.raises(ValueError, match="connection_string"):
            get_checkpointer("production")


# ── Checkpointer (MemorySaver — with langgraph mock) ─────────────────────────

class TestCheckpointerDevelopment:
    def test_development_returns_memory_saver_instance(self):
        mocks, mock_memory_saver, _ = _make_langgraph_mocks()
        with patch.dict(sys.modules, mocks):
            cp = get_checkpointer("development")
        assert isinstance(cp, mock_memory_saver)

    def test_development_creates_no_arg_instance(self):
        mocks, mock_memory_saver, _ = _make_langgraph_mocks()
        with patch.dict(sys.modules, mocks):
            cp = get_checkpointer("development")
        # Should be a valid object (not None)
        assert cp is not None


# ── route_after_review ────────────────────────────────────────────────────────

class TestRouteAfterReview:
    def test_human_review_when_score_above_threshold(self):
        state = make_state(quality_scores={"overall": 7.5})
        assert route_after_review(state) == "human_review"

    def test_human_review_at_exactly_threshold(self):
        state = make_state(quality_scores={"overall": 7.0})
        assert route_after_review(state) == "human_review"

    def test_escalate_when_revision_count_at_limit(self):
        state = make_state(quality_scores={"overall": 5.0}, revision_count=3)
        assert route_after_review(state) == "escalate"

    def test_escalate_when_revision_count_exceeds_limit(self):
        state = make_state(quality_scores={"overall": 3.0}, revision_count=5)
        assert route_after_review(state) == "escalate"

    def test_repair_when_score_low_and_revisions_remaining(self):
        state = make_state(quality_scores={"overall": 5.0}, revision_count=1)
        assert route_after_review(state) == "repair"

    def test_repair_when_quality_scores_none(self):
        state = make_state(quality_scores=None, revision_count=0)
        assert route_after_review(state) == "repair"

    def test_repair_when_quality_scores_empty_dict(self):
        state = make_state(quality_scores={}, revision_count=0)
        assert route_after_review(state) == "repair"


# ── route_after_human_review ──────────────────────────────────────────────────

class TestRouteAfterHumanReview:
    def test_validate_when_teacher_approved(self):
        state = make_state(teacher_approved=True)
        assert route_after_human_review(state) == "validate"

    def test_generate_when_teacher_rejected(self):
        state = make_state(teacher_approved=False)
        assert route_after_human_review(state) == "generate"

    def test_generate_when_teacher_approved_missing(self):
        state = make_state()
        state.pop("teacher_approved", None)
        assert route_after_human_review(state) == "generate"


# ── GraphStructure (with langgraph mock) ──────────────────────────────────────

class TestGraphStructure:
    def test_graph_compiles(self):
        from packages.agents.graph import build_oh_my_class_graph

        mocks, _, _ = _make_langgraph_mocks()
        with patch.dict(sys.modules, mocks):
            graph = build_oh_my_class_graph()
        assert graph is not None

    def test_graph_has_18_user_nodes(self):
        from packages.agents.graph import build_oh_my_class_graph

        mocks, _, nodes = _make_langgraph_mocks()
        with patch.dict(sys.modules, mocks):
            build_oh_my_class_graph()
        # 14 pipeline (incl. step_00_diagnostic, step_04b_roadmap) + 2 gates + healing_node + escalate_node  # noqa: E501
        assert len(nodes) == 18

    def test_graph_has_all_step_names(self):
        from packages.agents.graph import build_oh_my_class_graph

        mocks, _, nodes = _make_langgraph_mocks()
        with patch.dict(sys.modules, mocks):
            build_oh_my_class_graph()
        expected_nodes = [
            "step_00", "step_01", "step_02", "step_03", "gate_01",
            "step_04b", "step_05", "step_06", "step_07", "step_08",
            "step_09", "step_10", "step_10b", "gate_02",
            "step_11", "step_12", "healing_node", "escalate_node",
        ]
        for prefix in expected_nodes:
            assert any(n.startswith(prefix) for n in nodes), f"Missing {prefix}"

    def test_graph_total_nodes_including_start_end(self):
        from packages.agents.graph import build_oh_my_class_graph

        mocks, _, _ = _make_langgraph_mocks()
        with patch.dict(sys.modules, mocks):
            graph = build_oh_my_class_graph()
        # Compiled graph has __start__ + 18 user nodes + __end__ = 20
        assert len(graph.get_graph().nodes) == 20

    def test_graph_accepts_custom_checkpointer(self):
        from packages.agents.graph import build_oh_my_class_graph

        mocks, _, _ = _make_langgraph_mocks()
        with patch.dict(sys.modules, mocks):
            graph = build_oh_my_class_graph(checkpointer=MagicMock())
        assert graph is not None


# ── Quality gate router functions ─────────────────────────────────────────────

class TestRouteAfterSchema:
    def test_passes_when_schema_valid(self):
        assert route_after_schema(cast("OhMyClassState", {"schema_valid": True})) == "step_10_content_review"  # noqa: E501

    def test_heals_when_schema_invalid(self):
        assert route_after_schema(cast("OhMyClassState", {"schema_valid": False})) == "healing_node"

    def test_heals_when_schema_valid_missing(self):
        assert route_after_schema(cast("OhMyClassState", {})) == "healing_node"


class TestRouteAfterContentReview:
    def test_passes_when_review_passed(self):
        assert route_after_content_review(cast("OhMyClassState", {"content_review_passed": True})) == "step_10b_llm_judge"  # noqa: E501

    def test_heals_when_review_failed(self):
        assert route_after_content_review(cast("OhMyClassState", {"content_review_passed": False})) == "healing_node"  # noqa: E501

    def test_heals_when_review_missing(self):
        assert route_after_content_review(cast("OhMyClassState", {})) == "healing_node"


class TestRouteAfterJudge:
    def test_passes_when_score_at_threshold(self):
        assert route_after_judge(cast("OhMyClassState", {"judge_score": 7.0})) == "gate_02_content_approval"  # noqa: E501

    def test_passes_when_score_above_threshold(self):
        assert route_after_judge(cast("OhMyClassState", {"judge_score": 9.5})) == "gate_02_content_approval"  # noqa: E501

    def test_heals_when_score_below_threshold(self):
        assert route_after_judge(cast("OhMyClassState", {"judge_score": 6.9})) == "healing_node"

    def test_heals_when_score_missing(self):
        assert route_after_judge(cast("OhMyClassState", {})) == "healing_node"

    def test_heals_when_score_zero(self):
        assert route_after_judge(cast("OhMyClassState", {"judge_score": 0.0})) == "healing_node"


class TestRouteAfterExport:
    def test_finalizes_when_ready(self):
        assert route_after_export(cast("OhMyClassState", {"export_ready": True})) == "step_12_finalize"  # noqa: E501

    def test_escalates_when_not_ready(self):
        assert route_after_export(cast("OhMyClassState", {"export_ready": False})) == "escalate_node"  # noqa: E501

    def test_escalates_when_missing(self):
        assert route_after_export(cast("OhMyClassState", {})) == "escalate_node"
