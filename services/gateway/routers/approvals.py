"""Teacher approval gates — approve, edit, or reject blueprints and content.

Requires JWT authentication with teacher or admin role.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..auth.dependencies import require_teacher
from ..auth.models import User

router = APIRouter()


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


@router.post("/{run_id}/approve", response_model=ApprovalResponse)
async def approve(
    run_id: str,
    request: ApprovalRequest,
    current_user: Annotated[User, Depends(require_teacher)],
) -> ApprovalResponse:
    """POST /run/{id}/approve — Teacher approves current gate.

    Requires: JWT token with role=teacher or role=admin
    """
    # TODO: Verify run exists, resume graph with approval
    return ApprovalResponse(
        status="resumed",
        message=f"Run {run_id} approved and resumed",
        run_id=run_id,
    )


@router.post("/{run_id}/reject", response_model=ApprovalResponse)
async def reject(
    run_id: str,
    request: ApprovalRequest,
    current_user: Annotated[User, Depends(require_teacher)],
) -> ApprovalResponse:
    """POST /run/{id}/reject — Teacher rejects, triggers revision loop.

    Requires: JWT token with role=teacher or role=admin
    """
    if not request.feedback:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback required for rejection",
        )
    # TODO: Verify run exists, resume graph with rejection and feedback
    return ApprovalResponse(
        status="resumed",
        message=f"Run {run_id} rejected and resumed with feedback",
        run_id=run_id,
    )
