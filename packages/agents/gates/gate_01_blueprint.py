"""Gate 01 — Blueprint Approval: E3 HITL wrapper node.

Interrupts graph execution so the teacher can approve, reject, or edit the lesson plan.
Lead Agent is transparent to this gate — it only sees teacher_decision in state on resume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langgraph.types import interrupt

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


def gate_01_blueprint_approval(state: OhMyClassState) -> dict[str, Any]:
    """HITL gate: teacher reviews and approves the lesson blueprint.

    Interrupts graph execution. When resumed, injects teacher_decision,
    revision_feedback, and gate_payload into state.

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

    teacher_response: dict[str, Any] = interrupt({
        "gate": "blueprint_approval",
        "lesson_plan": lesson_plan,
        "run_id": state["run_id"],
    })

    action: str = teacher_response.get("action", "approve")
    feedback: str = teacher_response.get("feedback", "")
    edited_plan: dict[str, Any] | None = teacher_response.get("edited_lesson_plan")

    updates: dict[str, Any] = {
        "teacher_decision": action,
        "revision_feedback": feedback,
        "gate_payload": teacher_response,
    }

    if action == "edit" and edited_plan:
        updates["lesson_plan"] = edited_plan

    return updates
