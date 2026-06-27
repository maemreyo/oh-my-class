"""Run-level ownership checks for cross-tenant isolation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from services.gateway.auth.models import Role, User
from services.gateway.models import Run

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def check_run_owner(run_id: str, user: User, db: AsyncSession) -> bool:
    """Return True if *user* is authorized to access the given run.

    Authorization rules:
    - SYSTEM_ADMIN: always authorized (run must exist).
    - SCHOOL_ADMIN: authorized if the run's teacher belongs to the same
      organization (matched via the ``users`` table).
    - TEACHER / ADMIN: authorized only if ``run.teacher_id == user.user_id``.
    - Run not found → False.
    """
    statement = select(Run).where(Run.run_id == run_id)
    result = await db.execute(statement)
    run = result.scalar_one_or_none()

    if run is None:
        return False

    if user.role == Role.SYSTEM_ADMIN:
        return True

    if user.role == Role.SCHOOL_ADMIN:
        return await _check_same_organization(run.teacher_id, user, db)

    return run.teacher_id == user.user_id


async def _check_same_organization(
    run_teacher_id: str,
    user: User,
    db: AsyncSession,
) -> bool:
    """Check if run owner and requesting user share the same organization.

    Looks up the run owner's ``organization_id`` from the ``users`` DB table
    and compares it to ``user.organization_id`` (from the JWT token).

    Once ``organization_id`` is added to the ``users`` DB schema, this
    comparison works end-to-end.  Until then, returns False to fail-closed.
    """
    if not user.organization_id:
        return False

    from services.gateway.models import User as UserModel  # noqa: PLC0415

    statement = select(UserModel).where(UserModel.user_id == run_teacher_id)
    result = await db.execute(statement)
    owner = result.scalar_one_or_none()

    if owner is None:
        return False

    owner_org = getattr(owner, "organization_id", None)
    if owner_org is None:
        return False

    return owner_org == user.organization_id
