---
title: "Pipeline Backbone: Graph Builder + Checkpointer"
status: done
labels: []
created: 2026-06-23
github: 4
---

## What to build

Implement the LangGraph pipeline backbone in `packages/agents/graph.py` and `packages/agents/checkpointer.py`. Both files exist with stubs. Replace the stubs with working implementations.

## Current State

```python
# packages/agents/graph.py (lines 15-54)
def build_oh_my_class_graph(...) -> Any:
    # TODO: Implement with langgraph.StateGraph
    raise NotImplementedError("build_oh_my_class_graph() stub")

# packages/agents/checkpointer.py (lines 19-50)
def get_checkpointer(...) -> Any:
    # TODO: Implement dynamic import and instantiation
    raise NotImplementedError("get_checkpointer() stub")

# packages/agents/state.py — COMPLETE, no changes needed
# packages/agents/graph.py lines 57-79 — route_after_review, route_after_human_review — COMPLETE
```

## Implementation Spec

### 1. `checkpointer.py` — Replace stub (lines 19-50)

```python
"""Checkpointer factory for LangGraph state persistence."""

from __future__ import annotations

import importlib
from typing import Any

_CHECKPOINTER_MAP: dict[str, str] = {
    "development": "langgraph.checkpoint.memory.MemorySaver",
    "staging": "langgraph.checkpoint.sqlite.SqliteSaver",
    "production": "langgraph.checkpoint.postgres.PostgresSaver",
}


def get_checkpointer(environment: str = "development", **kwargs: Any) -> Any:
    """Create a checkpointer appropriate for the given environment.
    
    Args:
        environment: One of 'development', 'staging', 'production'.
        **kwargs: Additional arguments passed to the checkpointer constructor.
            For staging: db_path (default: 'omc_checkpoints.db').
            For production: connection_string (required).
    
    Returns:
        A LangGraph checkpointer instance.
    
    Raises:
        ValueError: If environment is not recognized.
        ImportError: If the required checkpointer package is not installed.
    """
    if environment not in _CHECKPOINTER_MAP:
        raise ValueError(
            f"Unknown environment '{environment}'. "
            f"Must be one of: {', '.join(_CHECKPOINTER_MAP)}"
        )
    
    module_path = _CHECKPOINTER_MAP[environment]
    module_name, class_name = module_path.rsplit(".", 1)
    
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        raise ImportError(
            f"Cannot import {module_name}. "
            f"Install the required package for '{environment}' environment."
        ) from e
    
    cls = getattr(module, class_name)
    
    # Handle different constructor signatures
    if environment == "development":
        return cls()
    elif environment == "staging":
        db_path = kwargs.get("db_path", "omc_checkpoints.db")
        return cls(db_path=db_path)
    elif environment == "production":
        connection_string = kwargs.get("connection_string")
        if not connection_string:
            raise ValueError("connection_string required for production environment")
        return cls.from_conn_string(connection_string)
    
    return cls(**kwargs)
```

### 2. `graph.py` — Replace stub (lines 15-54)

```python
"""LangGraph graph builder for the oh-my-class pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


def _make_dummy_node(step: int, name: str):
    """Create a dummy node for testing graph structure."""
    async def dummy_node(state: OhMyClassState) -> dict[str, Any]:
        return {"current_step": step}
    dummy_node.__name__ = name
    return dummy_node


async def _blueprint_approval(state: OhMyClassState) -> dict[str, Any]:
    """Interrupt gate for blueprint approval (Step 04)."""
    from langgraph.types import interrupt
    
    response = interrupt({
        "gate": "blueprint_approval",
        "lesson_plan": state.get("lesson_plan"),
        "actions": ["approve", "edit", "reject"],
    })
    
    return {
        "blueprint_approved": response.get("action") == "approve",
        "revision_feedback": response.get("feedback"),
    }


async def _content_approval(state: OhMyClassState) -> dict[str, Any]:
    """Interrupt gate for content approval (Step 11)."""
    from langgraph.types import interrupt
    
    response = interrupt({
        "gate": "content_approval",
        "artifacts": state.get("artifacts"),
        "quality_scores": state.get("quality_scores"),
        "actions": ["approve", "edit", "reject"],
    })
    
    return {
        "teacher_approved": response.get("action") == "approve",
        "revision_feedback": response.get("feedback"),
    }


def build_oh_my_class_graph(
    *,
    environment: str = "development",
    checkpointer: Any | None = None,
) -> Any:
    """Build and compile the oh-my-class LangGraph pipeline.
    
    Creates a StateGraph with 13 sequential steps, two interrupt() gates,
    and conditional routing for the quality review loop.
    
    Args:
        environment: One of 'development', 'staging', 'production'.
        checkpointer: Pre-configured checkpointer instance. If None,
            uses get_checkpointer() with the given environment.
    
    Returns:
        Compiled LangGraph graph ready for invocation.
    """
    from langgraph.graph import StateGraph, END
    from packages.agents.state import OhMyClassState
    from packages.agents.checkpointer import get_checkpointer
    
    # Get checkpointer if not provided
    if checkpointer is None:
        checkpointer = get_checkpointer(environment)
    
    # Create graph
    graph = StateGraph(OhMyClassState)
    
    # Add 13 nodes (using dummy nodes for now)
    graph.add_node("step_01_preflight", _make_dummy_node(1, "preflight"))
    graph.add_node("step_02_quickstart", _make_dummy_node(2, "quickstart"))
    graph.add_node("step_03_blueprint", _make_dummy_node(3, "blueprint"))
    graph.add_node("step_04_teacher_gate_1", _blueprint_approval)
    graph.add_node("step_05_pack_scope", _make_dummy_node(5, "pack_scope"))
    graph.add_node("step_06_visual_engine", _make_dummy_node(6, "visual_engine"))
    graph.add_node("step_07_research", _make_dummy_node(7, "research"))
    graph.add_node("step_08_generate", _make_dummy_node(8, "generate"))
    graph.add_node("step_09_import", _make_dummy_node(9, "import"))
    graph.add_node("step_10_review", _make_dummy_node(10, "review"))
    graph.add_node("step_11_teacher_gate_2", _content_approval)
    graph.add_node("step_12_validate", _make_dummy_node(12, "validate"))
    graph.add_node("step_13_export", _make_dummy_node(13, "export"))
    
    # Add sequential edges for linear steps
    graph.set_entry_point("step_01_preflight")
    graph.add_edge("step_01_preflight", "step_02_quickstart")
    graph.add_edge("step_02_quickstart", "step_03_blueprint")
    graph.add_edge("step_03_blueprint", "step_04_teacher_gate_1")
    graph.add_edge("step_04_teacher_gate_1", "step_05_pack_scope")
    graph.add_edge("step_05_pack_scope", "step_06_visual_engine")
    graph.add_edge("step_06_visual_engine", "step_07_research")
    graph.add_edge("step_07_research", "step_08_generate")
    graph.add_edge("step_08_generate", "step_09_import")
    graph.add_edge("step_09_import", "step_10_review")
    
    # Conditional edge after review
    graph.add_conditional_edges(
        "step_10_review",
        route_after_review,
        {
            "human_review": "step_11_teacher_gate_2",
            "escalate": END,
            "repair": "step_08_generate",  # Loop back to generate
        },
    )
    
    # Conditional edge after teacher gate 2
    graph.add_conditional_edges(
        "step_11_teacher_gate_2",
        route_after_human_review,
        {
            "validate": "step_12_validate",
            "generate": "step_08_generate",  # Loop back if rejected
        },
    )
    
    # Final edges
    graph.add_edge("step_12_validate", "step_13_export")
    graph.add_edge("step_13_export", END)
    
    # Compile with checkpointer
    return graph.compile(checkpointer=checkpointer)


# Existing routing functions (lines 57-79) — keep as-is
def route_after_review(state: OhMyClassState) -> str:
    """Route after quality review (Step 10)."""
    scores = state.get("quality_scores", {})
    overall = scores.get("overall", 0.0) if scores else 0.0
    if overall >= 7.0:
        return "human_review"
    if state.get("revision_count", 0) >= 3:
        return "escalate"
    return "repair"


def route_after_human_review(state: OhMyClassState) -> str:
    """Route after teacher gate 2 (Step 11)."""
    return "validate" if state.get("teacher_approved", False) else "generate"
```

## Acceptance criteria

- [ ] `get_checkpointer("development")` returns `MemorySaver` instance
- [ ] `get_checkpointer("staging")` returns `SqliteSaver` instance
- [ ] `get_checkpointer("production")` requires `connection_string`
- [ ] `get_checkpointer("unknown")` raises `ValueError`
- [ ] `build_oh_my_class_graph()` returns compiled LangGraph graph
- [ ] Graph has exactly 13 nodes
- [ ] Graph has sequential edges for steps 1-10
- [ ] Conditional edge routes to "human_review" when score >= 7.0
- [ ] Conditional edge routes to "escalate" when revision_count >= 3
- [ ] Conditional edge routes to "repair" otherwise
- [ ] `interrupt()` is called at Step 04 and Step 11
- [ ] Graph can be invoked with dummy state and completes

## Test suite

Create `packages/agents/tests/test_graph.py`:

```python
import pytest
from packages.agents.graph import (
    build_oh_my_class_graph,
    route_after_review,
    route_after_human_review,
)
from packages.agents.checkpointer import get_checkpointer


def make_state(**overrides):
    """Helper to create test state."""
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


class TestCheckpointer:
    def test_development_returns_memory_saver(self):
        from langgraph.checkpoint.memory import MemorySaver
        cp = get_checkpointer("development")
        assert isinstance(cp, MemorySaver)
    
    def test_unknown_raises_value_error(self):
        with pytest.raises(ValueError) as exc_info:
            get_checkpointer("unknown")
        assert "Unknown environment" in str(exc_info.value)


class TestRouteAfterReview:
    def test_pass_when_score_above_threshold(self):
        state = make_state(quality_scores={"overall": 7.5})
        assert route_after_review(state) == "human_review"
    
    def test_escalate_when_too_many_revisions(self):
        state = make_state(
            quality_scores={"overall": 5.0},
            revision_count=3,
        )
        assert route_after_review(state) == "escalate"
    
    def test_repair_when_score_low(self):
        state = make_state(
            quality_scores={"overall": 5.0},
            revision_count=1,
        )
        assert route_after_review(state) == "repair"


class TestRouteAfterHumanReview:
    def test_validate_when_approved(self):
        state = make_state(teacher_approved=True)
        assert route_after_human_review(state) == "validate"
    
    def test_generate_when_rejected(self):
        state = make_state(teacher_approved=False)
        assert route_after_human_review(state) == "generate"


class TestGraphStructure:
    def test_graph_has_13_nodes(self):
        graph = build_oh_my_class_graph()
        # Graph should have 13 nodes
        assert len(graph.get_graph().nodes) == 13
    
    def test_graph_compiles(self):
        graph = build_oh_my_class_graph()
        assert graph is not None
```

## File paths

| File | Action |
|------|--------|
| `packages/agents/checkpointer.py` | MODIFY: Replace stub (lines 19-50) with dynamic import |
| `packages/agents/graph.py` | MODIFY: Replace stub (lines 15-54) with StateGraph |
| `packages/agents/tests/test_graph.py` | CREATE: Full test suite |

## Dependencies

- `langgraph` — StateGraph, END, interrupt (already installed)
- `langgraph.checkpoint.memory` — MemorySaver (already installed)
- `langgraph.checkpoint.sqlite` — SqliteSaver (may need install)
- `langgraph.checkpoint.postgres` — PostgresSaver (may need install)
- `packages/agents/state.py` — OhMyClassState (already exists)

## Edge cases to handle

1. Unknown environment → ValueError
2. Missing package for staging/production → ImportError with helpful message
3. Production without connection_string → ValueError
4. Empty state → graph still completes (dummy nodes return partial state)
5. Loop back on repair → graph can re-invoke step_08_generate
