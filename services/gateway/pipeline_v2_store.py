from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import func, select, text

from services.gateway.models import Run, RunStatus
from services.gateway.pipeline_v2_models import (
    PipelineV2EventVisibility,
    RunEvent,
    RunStatusHistory,
)
from services.gateway.pipeline_v2_snapshot_store import (
    ArtifactSnapshotCreate,
    PipelineV2SnapshotStore,
)
from services.gateway.pipeline_v2_status import (
    StatusTransitionAccepted,
    validate_status_transition,
)
from services.gateway.pipeline_v2_types import JsonObject, RunId, TeacherId

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from packages.agents.pipeline_v2.stages import PipelineV2Stage

@dataclass(frozen=True, slots=True)
class PipelineV2RunCreate:
    run_id: RunId
    teacher_id: TeacherId
    raw_request: str
    class_info: JsonObject


@dataclass(frozen=True, slots=True)
class PipelineV2RunRead:
    run_id: RunId
    teacher_id: TeacherId
    status: RunStatus
    raw_request: str


@dataclass(frozen=True, slots=True)
class PipelineV2EventCreate:
    run_id: RunId
    event_name: str
    visibility: PipelineV2EventVisibility
    stage: PipelineV2Stage | None = None
    payload: JsonObject | None = None


@dataclass(frozen=True, slots=True)
class PipelineV2EventRead:
    run_id: RunId
    sequence: int
    event_name: str
    visibility: PipelineV2EventVisibility
    payload: JsonObject | None


@dataclass(frozen=True, slots=True)
class PipelineV2StatusTransition:
    run_id: RunId
    status: RunStatus
    stage: str | None
    reason: str | None


class PipelineV2RunStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_run(self, payload: PipelineV2RunCreate) -> None:
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
        )
        history = RunStatusHistory(
            run_id=payload.run_id,
            status=RunStatus.PENDING,
            stage=None,
            reason="created",
        )
        self._session.add_all([run, history])
        await self._session.flush()

    async def get_run(self, run_id: RunId, teacher_id: TeacherId) -> PipelineV2RunRead | None:
        statement = select(Run).where(Run.run_id == run_id, Run.teacher_id == teacher_id)
        result = await self._session.execute(statement)
        run = result.scalar_one_or_none()
        if run is None:
            return None
        return PipelineV2RunRead(
            run_id=RunId(run.run_id),
            teacher_id=TeacherId(run.teacher_id),
            status=run.status,
            raw_request=run.raw_request,
        )

    async def get_run_by_id(self, run_id: RunId) -> PipelineV2RunRead | None:
        statement = select(Run).where(Run.run_id == run_id)
        result = await self._session.execute(statement)
        run = result.scalar_one_or_none()
        if run is None:
            return None
        return PipelineV2RunRead(
            run_id=RunId(run.run_id),
            teacher_id=TeacherId(run.teacher_id),
            status=run.status,
            raw_request=run.raw_request,
        )

    async def transition_status(self, payload: PipelineV2StatusTransition) -> None:
        statement = select(Run).where(Run.run_id == payload.run_id).with_for_update()
        result = await self._session.execute(statement)
        run = result.scalar_one()
        transition = validate_status_transition(run.status, payload.status)
        match transition:
            case StatusTransitionAccepted():
                pass
            case rejected:
                raise InvalidRunStatusTransitionError(rejected.reason)
        run.status = payload.status
        self._session.add(RunStatusHistory(
            run_id=payload.run_id,
            status=payload.status,
            stage=payload.stage,
            reason=payload.reason,
        ))
        await self._session.flush()

    async def mark_stage_started(self, run_id: str, stage: PipelineV2Stage) -> None:
        await self.write_event(PipelineV2EventCreate(
            run_id=RunId(run_id),
            event_name=stage.started_event,
            visibility=PipelineV2EventVisibility.TEACHER,
            stage=stage,
        ))

    async def mark_stage_completed(self, run_id: str, stage: PipelineV2Stage) -> None:
        await self.write_event(PipelineV2EventCreate(
            run_id=RunId(run_id),
            event_name=stage.completed_event,
            visibility=PipelineV2EventVisibility.TEACHER,
            stage=stage,
        ))

    async def write_stage_event(
        self,
        run_id: str,
        stage: PipelineV2Stage,
        event_name: str,
    ) -> None:
        await self.write_event(PipelineV2EventCreate(
            run_id=RunId(run_id),
            event_name=event_name,
            visibility=PipelineV2EventVisibility.INTERNAL,
            stage=stage,
        ))

    async def write_event(self, payload: PipelineV2EventCreate) -> PipelineV2EventRead:
        sequence = await self._next_sequence(payload.run_id)
        event = RunEvent(
            run_id=payload.run_id,
            sequence=sequence,
            event_name=payload.event_name,
            stage=payload.stage.value if payload.stage is not None else None,
            visibility=payload.visibility,
            payload=payload.payload,
        )
        self._session.add(event)
        await self._session.flush()
        return PipelineV2EventRead(
            run_id=payload.run_id,
            sequence=sequence,
            event_name=payload.event_name,
            visibility=payload.visibility,
            payload=payload.payload,
        )

    async def replay_events(
        self,
        run_id: RunId,
        after_sequence: int = 0,
    ) -> list[PipelineV2EventRead]:
        statement = (
            select(RunEvent)
            .where(RunEvent.run_id == run_id, RunEvent.sequence > after_sequence)
            .order_by(RunEvent.sequence)
        )
        result = await self._session.execute(statement)
        return [
            PipelineV2EventRead(
                run_id=RunId(event.run_id),
                sequence=event.sequence,
                event_name=event.event_name,
                visibility=event.visibility,
                payload=event.payload,
            )
            for event in result.scalars().all()
        ]

    async def has_snapshot(self, content_hash: str) -> bool:
        return await PipelineV2SnapshotStore(self._session).has_snapshot(content_hash)

    async def create_snapshot(self, payload: ArtifactSnapshotCreate) -> str:
        snapshot = await PipelineV2SnapshotStore(self._session).create_snapshot(payload)
        return snapshot.content_hash

    async def _next_sequence(self, run_id: RunId) -> int:
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:run_id))"),
            {"run_id": run_id},
        )
        statement = select(func.coalesce(func.max(RunEvent.sequence), 0) + 1).where(
            RunEvent.run_id == run_id,
        )
        result = await self._session.execute(statement)
        return result.scalar_one()


class InvalidRunStatusTransitionError(RuntimeError):
    pass
