---
title: "HITL Gate Wrapper Nodes: E3 Pattern — Gates as Transparent Graph Nodes"
status: ready
labels: [architecture, agents, langgraph, hitl]
created: 2026-06-24
priority: p0
---

## What to build

Implement the two HITL gates (blueprint_approval, content_approval) as dedicated **wrapper nodes** in the graph. Gates sit between Lead Agent steps and handle `interrupt()` / resume transparently. The Lead Agent never calls `interrupt()` directly — it simply receives `teacher_decision` in state when it resumes.

**Design decision (grilling Q5):** E3 — wrapper nodes xử lý gates, Lead Agent xử lý content.

## Current State

```python
# packages/agents/graph.py
# step_04 and step_11 already exist as real interrupt gates
# BUT they are not separate "wrapper" nodes — they're mixed in with routing logic

# Route functions exist:
def route_after_review(state): ...     # checks overall_score
def route_after_human_review(state):   # checks teacher_approved
```

The existing gates work but don't follow E3 cleanly — gate logic is mixed into the main graph rather than isolated wrapper nodes.

## Target Architecture

```
graph flow:
[step_03_blueprint] → [gate_01_blueprint_approval] → [step_05_pack_scope]
                              ↑
                     interrupt() here
                     inject teacher_decision + gate_payload into state
                     Lead Agent resumes from step_05 with full context

[step_10_review] → conditional → [gate_02_content_approval] → [step_12_finalize]
                                          ↑
                                 interrupt() here
```

## Implementation Spec

### `packages/agents/gates/gate_01_blueprint.py` — NEW

```python
from __future__ import annotations
from langgraph.types import interrupt
from packages.agents.state import OhMyClassState


def gate_01_blueprint_approval(state: OhMyClassState) -> dict:
    """HITL gate: teacher reviews and approves the lesson blueprint.

    Interrupts graph execution. When resumed, injects teacher_decision
    and teacher_feedback into state so Lead Agent has full context.

    Expected resume payload:
        {
            "action": "approve" | "reject" | "edit",
            "feedback": str (required for reject/edit),
            "edited_lesson_plan": dict (only for action="edit")
        }
    """
    lesson_plan = state.get("lesson_plan")
    if not lesson_plan:
        raise ValueError("gate_01: lesson_plan must be set before blueprint approval")

    # interrupt() pauses graph here; resumes when API receives POST /run/{id}/approve
    teacher_response = interrupt({
        "gate": "blueprint_approval",
        "lesson_plan": lesson_plan,
        "run_id": state["run_id"],
    })

    # Normalize response
    action = teacher_response.get("action", "approve")
    feedback = teacher_response.get("feedback", "")
    edited_plan = teacher_response.get("edited_lesson_plan")

    updates: dict = {
        "teacher_decision": action,
        "teacher_feedback": feedback,
        "gate_payload": teacher_response,
    }

    # If teacher edited the plan, update it directly
    if action == "edit" and edited_plan:
        updates["lesson_plan"] = edited_plan

    return updates
```

### `packages/agents/gates/gate_02_content_approval.py` — NEW

```python
from __future__ import annotations
from langgraph.types import interrupt
from packages.agents.state import OhMyClassState


def gate_02_content_approval(state: OhMyClassState) -> dict:
    """HITL gate: teacher reviews and approves the generated artifacts.

    Expected resume payload:
        {
            "action": "approve" | "reject",
            "feedback": str (required for reject),
            "artifact_feedback": dict (per-artifact feedback, optional)
        }
    """
    artifacts = state.get("artifacts")
    if not artifacts:
        raise ValueError("gate_02: artifacts must be set before content approval")

    teacher_response = interrupt({
        "gate": "content_approval",
        "artifacts": artifacts,
        "review_results": state.get("review_results"),
        "run_id": state["run_id"],
    })

    action = teacher_response.get("action", "approve")
    feedback = teacher_response.get("feedback", "")

    return {
        "teacher_decision": action,
        "teacher_feedback": feedback,
        "gate_payload": teacher_response,
    }
```

### `packages/agents/gates/__init__.py`

```python
from packages.agents.gates.gate_01_blueprint import gate_01_blueprint_approval
from packages.agents.gates.gate_02_content_approval import gate_02_content_approval

__all__ = ["gate_01_blueprint_approval", "gate_02_content_approval"]
```

### `packages/agents/graph.py` — wire gates as nodes

```python
# Add gate nodes
builder.add_node("gate_01_blueprint_approval", gate_01_blueprint_approval)
builder.add_node("gate_02_content_approval", gate_02_content_approval)

# Wire edges
builder.add_edge("step_03_blueprint", "gate_01_blueprint_approval")
builder.add_conditional_edges(
    "gate_01_blueprint_approval",
    route_after_blueprint_gate,
    {
        "approve": "step_05_pack_scope",
        "reject": "step_03_blueprint",   # re-run planner with feedback
        "edit": "step_05_pack_scope",    # teacher edited plan, proceed
    },
)

builder.add_edge("step_10_review", "route_after_review_score")
# ... (existing score-based routing)
# When score passes threshold:
builder.add_edge("pre_gate_02", "gate_02_content_approval")
builder.add_conditional_edges(
    "gate_02_content_approval",
    route_after_content_gate,
    {
        "approve": "step_12_finalize",
        "reject": "step_08_generate",    # regenerate with feedback
    },
)
```

### Route functions for gates

```python
def route_after_blueprint_gate(state: OhMyClassState) -> str:
    """Route based on teacher's blueprint decision."""
    decision = state.get("teacher_decision", "approve")
    if decision in ("approve", "edit"):
        return "approve"
    return "reject"


def route_after_content_gate(state: OhMyClassState) -> str:
    """Route based on teacher's content decision."""
    decision = state.get("teacher_decision", "approve")
    return "approve" if decision == "approve" else "reject"
```

## State updates for "edit" action

When teacher uses "edit" action at Gate 1:
1. `gate_01_blueprint_approval` writes `edited_lesson_plan` to `state["lesson_plan"]`
2. Graph routes to `step_05_pack_scope` (proceed, not re-run planner)
3. Lead Agent at step_05 reads the updated `lesson_plan` from state — transparent

The Lead Agent never needs to know the gate happened. It just sees the (possibly updated) lesson_plan in state.

## Tests

```python
# packages/agents/gates/tests/test_gates.py

import pytest
from unittest.mock import patch
from packages.agents.gates import gate_01_blueprint_approval, gate_02_content_approval


def test_gate_01_raises_without_lesson_plan():
    state = {"run_id": "r-001", "teacher_id": "t-001"}
    with pytest.raises(ValueError, match="lesson_plan must be set"):
        gate_01_blueprint_approval(state)


def test_gate_01_injects_teacher_decision():
    with patch("packages.agents.gates.gate_01_blueprint.interrupt") as mock_interrupt:
        mock_interrupt.return_value = {"action": "approve", "feedback": ""}
        state = {
            "run_id": "r-001",
            "teacher_id": "t-001",
            "lesson_plan": {"topic": "Photosynthesis"},
        }
        result = gate_01_blueprint_approval(state)

    assert result["teacher_decision"] == "approve"
    assert "gate_payload" in result


def test_gate_01_edit_updates_lesson_plan():
    edited_plan = {"topic": "Photosynthesis (updated)", "grade_level": "Grade 5"}
    with patch("packages.agents.gates.gate_01_blueprint.interrupt") as mock_interrupt:
        mock_interrupt.return_value = {
            "action": "edit",
            "feedback": "Please update the topic",
            "edited_lesson_plan": edited_plan,
        }
        state = {
            "run_id": "r-001",
            "teacher_id": "t-001",
            "lesson_plan": {"topic": "Photosynthesis"},
        }
        result = gate_01_blueprint_approval(state)

    assert result["lesson_plan"] == edited_plan
    assert result["teacher_decision"] == "edit"


def test_route_after_blueprint_gate_approve():
    from packages.agents.graph import route_after_blueprint_gate
    state = {"teacher_decision": "approve"}
    assert route_after_blueprint_gate(state) == "approve"


def test_route_after_blueprint_gate_edit_proceeds():
    from packages.agents.graph import route_after_blueprint_gate
    state = {"teacher_decision": "edit"}
    assert route_after_blueprint_gate(state) == "approve"


def test_route_after_blueprint_gate_reject_reruns():
    from packages.agents.graph import route_after_blueprint_gate
    state = {"teacher_decision": "reject"}
    assert route_after_blueprint_gate(state) == "reject"
```

## Acceptance Criteria

- [ ] `gate_01_blueprint_approval` node: calls `interrupt()`, returns teacher_decision + gate_payload
- [ ] `gate_02_content_approval` node: calls `interrupt()`, returns teacher_decision + gate_payload
- [ ] `"edit"` action at Gate 1 updates `lesson_plan` in state directly
- [ ] `route_after_blueprint_gate()`: approve/edit → proceed; reject → re-run planner
- [ ] `route_after_content_gate()`: approve → finalize; reject → regenerate
- [ ] Lead Agent has NO knowledge of gates (does not call interrupt() itself)
- [ ] Gates live in `packages/agents/gates/` as separate module
- [ ] Tests cover approve / reject / edit flows for both gates

## Dependencies

- Blocked by: `agent-state-schema` (needs updated OhMyClassState with teacher_decision fields)
- Blocks: `lead-agent-react` integration (graph.py wiring)
