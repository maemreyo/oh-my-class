from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from services.gateway.auth.dependencies import require_admin
from services.gateway.auth.models import User
from services.gateway.slo_metrics import SloSnapshot, compute_slo_snapshot
from services.gateway.teaching_pack_db import get_teaching_pack_session

router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/slo")  # pyright: ignore[reportUntypedFunctionDecorator]
async def get_slo_snapshot(
    _current_user: Annotated[User, Depends(require_admin)],
    session: AsyncSession = Depends(get_teaching_pack_session),
) -> SloSnapshot:
    return await compute_slo_snapshot(session)
