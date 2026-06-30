from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, assert_never

from sqlalchemy import select

from services.gateway.models import Run, RunStatus, UnitRole
from services.gateway.teaching_pack_models import RunStatusHistory
from services.gateway.teaching_pack_types import JsonObject, RunId, TeacherId

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class UnitParentRunCreate:
    run_id: RunId
    teacher_id: TeacherId
    raw_request: str
    class_info: JsonObject
    lesson_sequence: JsonObject
    shared_research: JsonObject | None = None
    persona_snapshot: JsonObject | None = None
    retention_days: int | None = None


@dataclass(frozen=True, slots=True)
class UnitSessionRunCreate:
    run_id: RunId
    parent_run_id: RunId
    teacher_id: TeacherId
    session_id: str
    session_index: int
    raw_request: str
    class_info: JsonObject
    retention_days: int | None = None


@dataclass(frozen=True, slots=True)
class UnitSessionRunRead:
    run_id: RunId
    parent_run_id: RunId
    session_id: str
    session_index: int
    status: RunStatus
    raw_request: str


class UnitLifecycle(StrEnum):
    BLOCKED = "blocked"
    PARTIALLY_COMPLETE = "partially_complete"
    COMPLETE = "complete"


@dataclass(frozen=True, slots=True)
class UnitStatusRead:
    lifecycle: UnitLifecycle
    total_sessions: int
    completed_sessions: int
    active_sessions: int
    failed_sessions: int


class UnitRunStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_parent_run(self, payload: UnitParentRunCreate) -> None:
        run = Run(
            run_id=payload.run_id,
            teacher_id=payload.teacher_id,
            status=RunStatus.PENDING,
            current_step=1,
            raw_request=payload.raw_request,
            class_info=payload.class_info,
            artifact_types=[],
            theme="default",
            quality_passed=False,
            teacher_approved=False,
            revision_count=0,
            export_formats=["html"],
            tokens_used=0,
            cost_usd=0.0,
            retention_days=payload.retention_days,
            unit_role=UnitRole.UNIT_PARENT,
            lesson_sequence=payload.lesson_sequence,
            shared_research=payload.shared_research,
            persona_snapshot=payload.persona_snapshot,
        )
        self._session.add_all([run, self._status_history(payload.run_id, RunStatus.PENDING)])
        await self._session.flush()

    async def create_child_run(self, payload: UnitSessionRunCreate) -> None:
        parent = await self._parent_run(payload.parent_run_id)
        run = Run(
            run_id=payload.run_id,
            teacher_id=payload.teacher_id,
            status=RunStatus.PENDING,
            current_step=1,
            raw_request=payload.raw_request,
            class_info=payload.class_info,
            artifact_types=[],
            theme=parent.theme if parent is not None else "default",
            quality_passed=False,
            teacher_approved=False,
            revision_count=0,
            export_formats=["html"],
            tokens_used=0,
            cost_usd=0.0,
            retention_days=payload.retention_days,
            parent_run_id=payload.parent_run_id,
            session_id=payload.session_id,
            session_index=payload.session_index,
            unit_role=UnitRole.UNIT_SESSION,
            shared_research=parent.shared_research if parent is not None else None,
            persona_snapshot=parent.persona_snapshot if parent is not None else None,
        )
        self._session.add_all([run, self._status_history(payload.run_id, RunStatus.PENDING)])
        await self._session.flush()

    async def list_children(self, parent_run_id: RunId) -> list[UnitSessionRunRead]:
        statement = (
            select(Run)
            .where(Run.parent_run_id == parent_run_id, Run.unit_role == UnitRole.UNIT_SESSION)
            .order_by(Run.session_index)
        )
        result = await self._session.execute(statement)
        return [
            UnitSessionRunRead(
                run_id=RunId(run.run_id),
                parent_run_id=RunId(run.parent_run_id),
                session_id=run.session_id,
                session_index=run.session_index,
                status=run.status,
                raw_request=run.raw_request,
            )
            for run in result.scalars().all()
            if run.parent_run_id is not None
            and run.session_id is not None
            and run.session_index is not None
        ]

    async def get_lesson_sequence(self, parent_run_id: RunId) -> JsonObject | None:
        statement = select(Run.lesson_sequence).where(
            Run.run_id == parent_run_id,
            Run.unit_role == UnitRole.UNIT_PARENT,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def compute_unit_status(self, parent_run_id: RunId) -> UnitStatusRead:
        children = await self.list_children(parent_run_id)
        completed = sum(child.status is RunStatus.COMPLETED for child in children)
        active = sum(_is_active_status(child.status) for child in children)
        failed = sum(child.status in {RunStatus.FAILED, RunStatus.CANCELLED} for child in children)
        return UnitStatusRead(
            lifecycle=_unit_lifecycle(len(children), completed, active, failed),
            total_sessions=len(children),
            completed_sessions=completed,
            active_sessions=active,
            failed_sessions=failed,
        )

    def _status_history(self, run_id: RunId, status: RunStatus) -> RunStatusHistory:
        return RunStatusHistory(run_id=run_id, status=status, stage=None, reason="created")

    async def _parent_run(self, parent_run_id: RunId) -> Run | None:
        result = await self._session.execute(select(Run).where(Run.run_id == parent_run_id))
        return result.scalar_one_or_none()


def _is_active_status(status: RunStatus) -> bool:
    match status:
        case RunStatus.PENDING | RunStatus.PLANNING | RunStatus.RESEARCHING | RunStatus.GENERATING:
            return True
        case RunStatus.REVIEWING | RunStatus.AWAITING_APPROVAL | RunStatus.EXPORTING:
            return True
        case RunStatus.COMPLETED | RunStatus.FAILED | RunStatus.CANCELLED:
            return False
        case unreachable:
            assert_never(unreachable)


def _unit_lifecycle(
    total_sessions: int,
    completed_sessions: int,
    active_sessions: int,
    failed_sessions: int,
) -> UnitLifecycle:
    if total_sessions == 0:
        return UnitLifecycle.BLOCKED
    if completed_sessions == total_sessions:
        return UnitLifecycle.COMPLETE
    if active_sessions == 0 and completed_sessions == 0 and failed_sessions > 0:
        return UnitLifecycle.BLOCKED
    return UnitLifecycle.PARTIALLY_COMPLETE
