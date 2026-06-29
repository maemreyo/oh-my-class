from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from services.gateway.notifications import notify_run_completed, notify_run_failed
from services.gateway.teaching_pack_snapshot_store import ArtifactSnapshotCreate
from services.gateway.teaching_pack_store import (
    TeachingPackEventCreate,
    TeachingPackGateCreate,
    TeachingPackRunRead,
    TeachingPackStatusTransition,
)
from services.gateway.teaching_pack_types import RunId

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class TeachingPackRunEventStore(Protocol):
    async def get_run_by_id(self, run_id: RunId) -> TeachingPackRunRead | None: ...

    async def transition_status(self, payload: TeachingPackStatusTransition) -> None: ...

    async def write_event(self, payload: TeachingPackEventCreate) -> object: ...


class TeachingPackFailureStore(TeachingPackRunEventStore, Protocol):

    async def create_snapshot(self, payload: ArtifactSnapshotCreate) -> str: ...

    async def open_gate(self, payload: TeachingPackGateCreate) -> None: ...


class TeachingPackNotificationSink(Protocol):
    async def notify_completed(self, run_id: RunId, teacher_id: str) -> None: ...

    async def notify_failed(self, run_id: RunId, teacher_id: str, error_summary: str) -> None: ...


class InAppTeachingPackNotificationSink:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def notify_completed(self, run_id: RunId, teacher_id: str) -> None:
        await notify_run_completed(run_id, teacher_id, self._session)

    async def notify_failed(self, run_id: RunId, teacher_id: str, error_summary: str) -> None:
        await notify_run_failed(run_id, teacher_id, error_summary, self._session)
