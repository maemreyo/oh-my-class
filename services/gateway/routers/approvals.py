"""Teacher approval gates — approve, edit, or reject blueprints and content.

Requires JWT authentication with teacher or admin role.
"""

from enum import StrEnum
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from ..auth.dependencies import require_teacher
from ..auth.models import User

router = APIRouter()

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


@router.post("/{run_id}/approve", response_model=ApprovalResponse)  # pyright: ignore[reportUntypedFunctionDecorator]
async def approve(
    run_id: str,
    request: ApprovalRequest,
    http_request: Request,
    current_user: Annotated[User, Depends(require_teacher)],
) -> ApprovalResponse:
    _ = (run_id, request, http_request, current_user)
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Legacy /run approvals are decommissioned; use /teaching-packs gate responses.",
    )


@router.post("/{run_id}/reject", response_model=ApprovalResponse)  # pyright: ignore[reportUntypedFunctionDecorator]
async def reject(
    run_id: str,
    request: ApprovalRequest,
    http_request: Request,
    current_user: Annotated[User, Depends(require_teacher)],
) -> ApprovalResponse:
    _ = (run_id, request, http_request, current_user)
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Legacy /run approvals are decommissioned; use /teaching-packs gate responses.",
    )
