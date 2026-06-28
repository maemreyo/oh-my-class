"""Shared dependencies for pipeline V2 route modules."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from services.gateway.auth.models import Role, User  # noqa: TC001
from services.gateway.auth.ownership import check_run_owner
from services.gateway.backpressure import BackpressureConfig
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_store import TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId
from services.gateway.soft_delete import is_run_deleted

TEACHING_PACK_SESSION = Depends(get_teaching_pack_session)


def _default_backpressure_config() -> BackpressureConfig:
    return BackpressureConfig()


BACKPRESSURE_CONFIG = Depends(_default_backpressure_config)


async def _get_run_with_ownership(
    run_id: str,
    user: User,
    session: AsyncSession,
):
    """Fetch a run enforcing cross-tenant ownership rules.

    SYSTEM_ADMIN bypasses the teacher_id filter; all other roles must own
    the run.  Returns the run or raises 403/404.
    """
    typed_run_id = RunId(run_id)
    store = TeachingPackRunStore(session)

    if user.role == Role.SYSTEM_ADMIN:
        run = await store.get_run_by_id(typed_run_id)
    else:
        run = await store.get_run(typed_run_id, TeacherId(user.user_id))

    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run_not_found")

    if await is_run_deleted(run_id, session):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run_not_found")

    if not await check_run_owner(run_id, user, session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not_run_owner")

    return run
