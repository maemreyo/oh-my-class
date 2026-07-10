from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import event, func, select, text
from sqlalchemy.orm import Session

from packages.agents.events import ObservabilityEvent
from services.gateway.models import Run, RunStatus
from services.gateway.observability_events import observability_event_row
from services.gateway.teaching_pack_event_bus import notify_run_event
from services.gateway.teaching_pack_models import (
    GateInterrupt,
    GateInterruptStatus,
    TeachingPackEventVisibility,
    RunEvent,
    RunStatusHistory,
)
from services.gateway.teaching_pack_snapshot_store import (
    ArtifactSnapshotCreate,
    TeachingPackSnapshotStore,
)
from services.gateway.teaching_pack_status import (
    StatusTransitionAccepted,
    validate_status_transition,
)
from services.gateway.teaching_pack_types import JsonObject, RunId, TeacherId

_PENDING_EVENT_RUN_IDS = "teaching_pack_event_run_ids"


@event.listens_for(Session, "after_commit")
def _notify_teaching_pack_events_after_commit(session: Session) -> None:
    run_ids = session.info.pop(_PENDING_EVENT_RUN_IDS, set())
    for run_id in run_ids:
        notify_run_event(RunId(run_id))


@event.listens_for(Session, "after_rollback")
def _clear_teaching_pack_events_after_rollback(session: Session) -> None:
    session.info.pop(_PENDING_EVENT_RUN_IDS, None)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from packages.agents.teaching_pack.stages import TeachingPackStage

@dataclass(frozen=True, slots=True)
class TeachingPackRunCreate:
    run_id: RunId
    teacher_id: TeacherId
    raw_request: str
    class_info: JsonObject
    retention_days: int | None = None


@dataclass(frozen=True, slots=True)
class TeachingPackRunRead:
    run_id: RunId
    teacher_id: TeacherId
    status: RunStatus
    raw_request: str


@dataclass(frozen=True, slots=True)
class TeachingPackEventCreate:
    run_id: RunId
    event_name: str
    visibility: TeachingPackEventVisibility
    stage: TeachingPackStage | None = None
    payload: JsonObject | None = None


@dataclass(frozen=True, slots=True)
class TeachingPackEventRead:
    run_id: RunId
    sequence: int
    event_name: str
    visibility: TeachingPackEventVisibility
    payload: JsonObject | None


@dataclass(frozen=True, slots=True)
class TeachingPackStatusTransition:
    run_id: RunId
    status: RunStatus
    stage: str | None
    reason: str | None


@dataclass(frozen=True, slots=True)
class TeachingPackGateCreate:
    gate_id: str
    run_id: RunId
    gate_name: str
    payload: JsonObject


class TeachingPackRunStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_run(self, payload: TeachingPackRunCreate) -> None:
        run = Run(
            run_id=payload.run_id,
            teacher_id=payload.teacher_id,
            status=RunStatus.PENDING,
            current_step=1,
            raw_request=payload.raw_request,
            class_info=payload.class_info,
            retention_days=payload.retention_days,
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

    async def get_run(self, run_id: RunId, teacher_id: TeacherId) -> TeachingPackRunRead | None:
        statement = select(Run).where(Run.run_id == run_id, Run.teacher_id == teacher_id)
        result = await self._session.execute(statement)
        run = result.scalar_one_or_none()
        if run is None:
            return None
        return TeachingPackRunRead(
            run_id=RunId(run.run_id),
            teacher_id=TeacherId(run.teacher_id),
            status=run.status,
            raw_request=run.raw_request,
        )

    async def get_run_by_id(self, run_id: RunId) -> TeachingPackRunRead | None:
        statement = select(Run).where(Run.run_id == run_id)
        result = await self._session.execute(statement)
        run = result.scalar_one_or_none()
        if run is None:
            return None
        return TeachingPackRunRead(
            run_id=RunId(run.run_id),
            teacher_id=TeacherId(run.teacher_id),
            status=run.status,
            raw_request=run.raw_request,
        )

    async def transition_status(self, payload: TeachingPackStatusTransition) -> None:
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
        await self.write_event(TeachingPackEventCreate(
            run_id=payload.run_id,
            event_name="teaching_pack.status.changed",
            visibility=TeachingPackEventVisibility.TEACHER,
            payload={
                "status": payload.status.value,
                "stage": payload.stage,
                "reason": payload.reason,
            },
        ))
        await self._session.flush()

    async def mark_stage_started(self, run_id: str, stage: TeachingPackStage) -> None:
        await self.write_event(TeachingPackEventCreate(
            run_id=RunId(run_id),
            event_name=stage.started_event,
            visibility=TeachingPackEventVisibility.TEACHER,
            stage=stage,
        ))

    async def mark_stage_completed(self, run_id: str, stage: TeachingPackStage) -> None:
        await self.write_event(TeachingPackEventCreate(
            run_id=RunId(run_id),
            event_name=stage.completed_event,
            visibility=TeachingPackEventVisibility.TEACHER,
            stage=stage,
        ))

    async def write_stage_event(
        self,
        run_id: str,
        stage: TeachingPackStage,
        event_name: str,
    ) -> None:
        await self.write_event(TeachingPackEventCreate(
            run_id=RunId(run_id),
            event_name=event_name,
            visibility=TeachingPackEventVisibility.INTERNAL,
            stage=stage,
        ))

    async def write_event(self, payload: TeachingPackEventCreate) -> TeachingPackEventRead:
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
        run_ids = self._session.sync_session.info.setdefault(_PENDING_EVENT_RUN_IDS, set())
        run_ids.add(str(payload.run_id))
        return TeachingPackEventRead(
            run_id=payload.run_id,
            sequence=sequence,
            event_name=payload.event_name,
            visibility=payload.visibility,
            payload=payload.payload,
        )

    async def write_observability_event(
        self,
        event: ObservabilityEvent,
        visibility: TeachingPackEventVisibility = TeachingPackEventVisibility.INTERNAL,
    ) -> TeachingPackEventRead:
        sequence = await self._next_sequence(RunId(event.run_id))
        row = observability_event_row(event, sequence, visibility)
        self._session.add(row)
        await self._session.flush()
        run_ids = self._session.sync_session.info.setdefault(_PENDING_EVENT_RUN_IDS, set())
        run_ids.add(event.run_id)
        return TeachingPackEventRead(
            run_id=RunId(event.run_id),
            sequence=sequence,
            event_name=event.event_type,
            visibility=visibility,
            payload=row.payload,
        )

    async def replay_events(
        self,
        run_id: RunId,
        after_sequence: int = 0,
    ) -> list[TeachingPackEventRead]:
        statement = (
            select(RunEvent)
            .where(RunEvent.run_id == run_id, RunEvent.sequence > after_sequence)
            .order_by(RunEvent.sequence)
        )
        result = await self._session.execute(statement)
        return [
            TeachingPackEventRead(
                run_id=RunId(event.run_id),
                sequence=event.sequence,
                event_name=event.event_name,
                visibility=event.visibility,
                payload=event.payload,
            )
            for event in result.scalars().all()
        ]

    async def list_events_by_name(self, run_id: RunId, event_name: str) -> list[TeachingPackEventRead]:
        """SDE-05: fetch one event type for a run (e.g. `content_version.created`)
        so the version-history list can look up each version's authority/rationale
        without replaying the run's entire event log."""
        statement = (
            select(RunEvent)
            .where(RunEvent.run_id == run_id, RunEvent.event_name == event_name)
            .order_by(RunEvent.sequence)
        )
        result = await self._session.execute(statement)
        return [
            TeachingPackEventRead(
                run_id=RunId(event.run_id),
                sequence=event.sequence,
                event_name=event.event_name,
                visibility=event.visibility,
                payload=event.payload,
            )
            for event in result.scalars().all()
        ]

    async def has_snapshot(self, content_hash: str) -> bool:
        return await TeachingPackSnapshotStore(self._session).has_snapshot(content_hash)

    async def create_snapshot(self, payload: ArtifactSnapshotCreate) -> str:
        snapshot = await TeachingPackSnapshotStore(self._session).create_snapshot(payload)
        return snapshot.content_hash

    async def open_gate(self, payload: TeachingPackGateCreate) -> None:
        self._session.add(GateInterrupt(
            gate_id=payload.gate_id,
            run_id=payload.run_id,
            gate_name=payload.gate_name,
            status=GateInterruptStatus.ACTIVE,
            payload=payload.payload,
            expires_at=None,
        ))
        await self._session.flush()

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
