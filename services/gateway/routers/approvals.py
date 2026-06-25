"""Teacher approval gates — approve, edit, or reject blueprints and content.

Requires JWT authentication with teacher or admin role.
"""

from enum import StrEnum
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from langgraph.types import Command
from pydantic import BaseModel

from ..auth.dependencies import require_teacher
from ..auth.models import Role, User
from ..exceptions import (
    AuthorizationError,
    NotFoundError,
    PipelineError,
    ValidationError,
)
from .runs import _derive_status, emit_run_event

router = APIRouter()

_VALID_GATES = frozenset({"blueprint_approval", "content_approval"})


class ApprovalAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class ApprovalRequest(BaseModel):
    action: ApprovalAction
    feedback: str | None = None
    edits: dict[str, Any] | None = None


class ApprovalResponse(BaseModel):
    status: str
    message: str
    run_id: str


def _require_gate(run_data: dict[str, Any]) -> str:
    state = run_data.get("state", {})

    # Check __interrupt__ first (LangGraph Interrupt objects)
    interrupt_list = state.get("__interrupt__")
    if interrupt_list and isinstance(interrupt_list, list):
        interrupt_data = interrupt_list[0]
        # Interrupt objects have .value attr; serialized dicts have ["value"] key
        if hasattr(interrupt_data, "value"):
            value = interrupt_data.value
        elif isinstance(interrupt_data, dict):
            value = interrupt_data.get("value", interrupt_data)
        else:
            value = None
        gate_type = value.get("gate") if isinstance(value, dict) else None
        if gate_type in _VALID_GATES:
            return gate_type

    # Fallback: check gate_payload (legacy format)
    gate_payload = state.get("gate_payload")
    gate_type = gate_payload.get("gate") if gate_payload else None
    if gate_type not in _VALID_GATES:
        raise ValidationError(
            message="Run is not at an approval gate",
            details=[{"current_status": run_data.get("status", "unknown")}],
        )
    return gate_type


def _require_owner(run_data: dict[str, Any], user: User) -> None:
    if user.role == Role.ADMIN:
        return
    if run_data.get("teacher_id") != user.user_id:
        raise AuthorizationError(message="You do not have access to this run")


@router.post("/{run_id}/approve", response_model=ApprovalResponse)  # pyright: ignore[reportUntypedFunctionDecorator]
async def approve(
    run_id: str,
    request: ApprovalRequest,
    http_request: Request,
    current_user: Annotated[User, Depends(require_teacher)],
) -> ApprovalResponse:
    runs = http_request.app.state.runs
    run_data = runs.get(run_id)
    if not run_data:
        raise NotFoundError(message=f"Run {run_id} not found")

    _require_owner(run_data, current_user)

    if request.action != ApprovalAction.APPROVE:
        raise HTTPException(
            status_code=422,
            detail=f"POST /approve requires action=approve, got {request.action!r}",
        )

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
    if request.action != ApprovalAction.REJECT:
        raise HTTPException(
            status_code=422,
            detail=f"POST /reject requires action=reject, got {request.action!r}",
        )

    if not request.feedback:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback required for rejection",
        )

    runs = http_request.app.state.runs
    run_data = runs.get(run_id)
    if not run_data:
        raise NotFoundError(message=f"Run {run_id} not found")

    _require_owner(run_data, current_user)

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
