"""Gate 02 — Content Approval: E3 HITL wrapper node.

Interrupts graph execution so the teacher can approve or reject the generated artifacts.
Lead Agent is transparent to this gate — it only sees teacher_decision in state on resume.
"""

from __future__ import annotations

from typing import Any

from langgraph.types import interrupt

from packages.agents.gates.state import GateState


def gate_02_content_approval(state: GateState) -> dict[str, Any]:
    """HITL gate: teacher reviews and approves the generated artifacts.

    Interrupts graph execution. When resumed, injects teacher_decision,
    revision_feedback, and gate_payload into state.

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

    teacher_response: dict[str, Any] = interrupt({
        "gate": "content_approval",
        "artifacts": artifacts,
        "review_results": state.get("quality_scores"),
        "run_id": state["run_id"],
    })

    action: str = teacher_response.get("action", "approve")
    feedback: str = teacher_response.get("feedback", "")

    return {
        "teacher_approved": action == "approve",
        "teacher_decision": action,
        "revision_feedback": feedback,
        "gate_payload": teacher_response,
    }
