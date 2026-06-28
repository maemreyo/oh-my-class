"""Soft-delete operations for Teaching Pack runs.

Soft-deleted runs remain in the database but are hidden from normal
queries.  A background purge job (see ``purge.py``) permanently removes
them after the retention window expires.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from services.gateway.models import Run
from services.gateway.teaching_pack_models import TeachingPackEventVisibility
from services.gateway.teaching_pack_store import TeachingPackEventCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def soft_delete_run(
    run_id: str,
    deleted_by: str,
    db: AsyncSession,
) -> None:
    """Mark *run_id* as soft-deleted.

    Sets ``deleted_at`` and ``deleted_by`` on the run row and emits a
    ``run.soft_deleted`` event.
    """
    typed_run_id = RunId(run_id)
    now = datetime.now(UTC)
    statement = select(Run).where(Run.run_id == typed_run_id).with_for_update()
    result = await db.execute(statement)
    run = result.scalar_one_or_none()
    if run is None:
        return
    run.deleted_at = now
    run.deleted_by = deleted_by
    await db.flush()

    store = TeachingPackRunStore(db)
    await store.write_event(TeachingPackEventCreate(
        run_id=typed_run_id,
        event_name="run.soft_deleted",
        visibility=TeachingPackEventVisibility.ADMIN,
        payload={"deleted_by": deleted_by},
    ))
    await db.flush()


async def restore_run(
    run_id: str,
    restored_by: str,
    db: AsyncSession,
) -> None:
    """Restore a soft-deleted run.

    Clears ``deleted_at`` and ``deleted_by`` and emits a ``run.restored``
    event.
    """
    typed_run_id = RunId(run_id)
    statement = select(Run).where(Run.run_id == typed_run_id).with_for_update()
    result = await db.execute(statement)
    run = result.scalar_one_or_none()
    if run is None:
        return
    run.deleted_at = None
    run.deleted_by = None
    await db.flush()

    store = TeachingPackRunStore(db)
    await store.write_event(TeachingPackEventCreate(
        run_id=typed_run_id,
        event_name="run.restored",
        visibility=TeachingPackEventVisibility.ADMIN,
        payload={"restored_by": restored_by},
    ))
    await db.flush()


async def is_run_deleted(run_id: str, db: AsyncSession) -> bool:
    """Return ``True`` if *run_id* is soft-deleted."""
    typed_run_id = RunId(run_id)
    statement = select(Run.deleted_at).where(Run.run_id == typed_run_id)
    result = await db.execute(statement)
    deleted_at = result.scalar_one_or_none()
    return deleted_at is not None
