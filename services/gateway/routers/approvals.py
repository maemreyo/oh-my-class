"""Teacher approval gates — approve, edit, or reject blueprints and content.

Requires JWT authentication with teacher or admin role.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from langgraph.types import Command
from pydantic import BaseModel

from ..auth.dependencies import require_teacher
from ..auth.models import User
from ..exceptions import NotFoundError, PipelineError, ValidationError
from .runs import _derive_status, emit_run_event

router = APIRouter()

_VALID_GATES = frozenset({"blueprint_approval", "content_approval"})


class ApprovalRequest(BaseModel):
    """Request body for approval/rejection."""

    action: str
    feedback: str | None = None
    edits: dict[str, Any] | None = None


class ApprovalResponse(BaseModel):
    """Response from approval endpoint."""

    status: str
    message: str
    run_id: str


def _require_gate(run_data: dict[str, Any]) -> str:
    """Return the current gate name or raise if not at a valid approval gate."""
    state = run_data.get("state", {})
    gate_payload = state.get("gate_payload")
    gate_type = gate_payload.get("gate") if gate_payload else None
    if gate_type not in _VALID_GATES:
        raise ValidationError(
            message="Run is not at an approval gate",
            details=[{"current_status": run_data.get("status", "unknown")}],
        )
    return gate_type


@router.post("/{run_id}/approve", response_model=ApprovalResponse)  # pyright: ignore[reportUntypedFunctionDecorator]
async def approve(
    run_id: str,
    request: ApprovalRequest,
    http_request: Request,
    current_user: Annotated[User, Depends(require_teacher)],
) -> ApprovalResponse:
    """POST /run/{id}/approve — Teacher approves blueprint or content.

    Detects whether the run is at Gate 1 (blueprint) or Gate 2 (content),
    resumes the interrupted graph thread with an approve command, and
    advances state toward the next pipeline phase.
    """
    runs = http_request.app.state.runs
    run_data = runs.get(run_id)
    if not run_data:
        raise NotFoundError(message=f"Run {run_id} not found")

    gate_type = _require_gate(run_data)

    graph = http_request.app.state.graph
    try:
        new_state = await graph.ainvoke(
            Command(resume={"action": "approve", "feedback": request.feedback or ""}),
            config={"configurable": {"thread_id": run_id}},
        )
    except Exception as exc:
        raise PipelineError(
            message=f"Graph resume failed: {exc}",
            run_id=run_id,
        ) from exc

    run_status = _derive_status(new_state)
    runs[run_id]["state"] = new_state
    runs[run_id]["status"] = run_status

    emit_run_event(run_id, "gate_approved", {
        "gate": gate_type,
        "status": run_status,
    })

    if gate_type == "content_approval":
        message = f"Run {run_id} content approved and resumed"
    else:
        message = f"Run {run_id} blueprint approved and resumed"

    return ApprovalResponse(
        status="resumed",
        message=message,
        run_id=run_id,
    )


@router.post("/{run_id}/reject", response_model=ApprovalResponse)  # pyright: ignore[reportUntypedFunctionDecorator]
async def reject(
    run_id: str,
    request: ApprovalRequest,
    http_request: Request,
    current_user: Annotated[User, Depends(require_teacher)],
) -> ApprovalResponse:
    """POST /run/{id}/reject — Teacher rejects blueprint or content.

    Detects whether the run is at Gate 1 (blueprint) or Gate 2 (content),
    requires feedback text, records revision_feedback in state and resumes
    the graph, which loops back to the appropriate generation step.
    """
    if not request.feedback:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback required for rejection",
        )

    runs = http_request.app.state.runs
    run_data = runs.get(run_id)
    if not run_data:
        raise NotFoundError(message=f"Run {run_id} not found")

    gate_type = _require_gate(run_data)

    graph = http_request.app.state.graph
    try:
        new_state = await graph.ainvoke(
            Command(resume={"action": "reject", "feedback": request.feedback}),
            config={"configurable": {"thread_id": run_id}},
        )
    except Exception as exc:
        raise PipelineError(
            message=f"Graph resume failed: {exc}",
            run_id=run_id,
        ) from exc

    run_status = _derive_status(new_state)
    runs[run_id]["state"] = new_state
    runs[run_id]["status"] = run_status

    emit_run_event(run_id, "gate_rejected", {
        "gate": gate_type,
        "status": run_status,
        "feedback": request.feedback[:200] if request.feedback else "",
    })

    if gate_type == "content_approval":
        message = f"Run {run_id} content rejected and resumed with feedback"
    else:
        message = f"Run {run_id} rejected and resumed with feedback"

    return ApprovalResponse(
        status="resumed",
        message=message,
        run_id=run_id,
    )
