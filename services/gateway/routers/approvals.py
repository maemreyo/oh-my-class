"""Teacher approval gates — approve, edit, or reject blueprints and content.

Requires JWT authentication with teacher or admin role.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from ..auth.dependencies import require_teacher
from ..auth.models import User

router = APIRouter()


@router.post("/{run_id}/approve")
async def approve(
    run_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
):
    """POST /run/{id}/approve — Teacher approves current gate.

    Requires: JWT token with role=teacher or role=admin
    """
    # TODO: Verify run exists, update state, resume pipeline
    return {
        "status": "approved",
        "run_id": run_id,
        "approved_by": current_user.user_id,
        "role": current_user.role,
    }


@router.post("/{run_id}/reject")
async def reject(
    run_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
):
    """POST /run/{id}/reject — Teacher rejects, triggers revision loop.

    Requires: JWT token with role=teacher or role=admin
    """
    # TODO: Verify run exists, set revision feedback, resume pipeline
    return {
        "status": "rejected",
        "run_id": run_id,
        "rejected_by": current_user.user_id,
        "role": current_user.role,
    }
