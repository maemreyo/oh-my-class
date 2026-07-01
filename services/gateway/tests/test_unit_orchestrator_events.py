from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import patch

import pytest

from common.contracts.lesson_sequence import LessonSequence, SessionPlan
from services.gateway.teaching_pack_job_store import RunJobCreate
from services.gateway.teaching_pack_models import TeachingPackEventVisibility
from services.gateway.teaching_pack_store import TeachingPackEventCreate
from services.gateway.teaching_pack_types import JsonObject, RunId, TeacherId
from services.gateway.unit_orchestrator import OrchestratorAction, UnitOrchestrator
from services.gateway.unit_run_store import UnitSessionRunCreate, UnitSessionRunRead

pytestmark = pytest.mark.asyncio


@dataclass(frozen=True, slots=True)
class _ParentRun:
    teacher_id: TeacherId
    raw_request: str
    class_info: JsonObject
    retention_days: int


@dataclass(frozen=True, slots=True)
class _ScalarResult:
    parent_run: _ParentRun

    def scalar_one_or_none(self) -> _ParentRun:
        return self.parent_run


@dataclass(slots=True)
class _Session:
    parent_run: _ParentRun

    async def execute(self, _statement) -> _ScalarResult:
        return _ScalarResult(self.parent_run)


@dataclass(slots=True)
class _UnitRunStore:
    lesson_sequence: JsonObject
    created_children: list[UnitSessionRunCreate] = field(default_factory=list)

    async def get_lesson_sequence(self, _parent_run_id: RunId) -> JsonObject:
        return self.lesson_sequence

    async def list_children(self, _parent_run_id: RunId) -> list[UnitSessionRunRead]:
        return []

    async def create_child_run(self, payload: UnitSessionRunCreate) -> None:
        self.created_children.append(payload)


@dataclass(slots=True)
class _JobStore:
    enqueued_jobs: list[RunJobCreate] = field(default_factory=list)

    async def enqueue(self, payload: RunJobCreate) -> None:
        self.enqueued_jobs.append(payload)


@dataclass(slots=True)
class _EventStore:
    session: _Session

    written_events: list[TeachingPackEventCreate] = field(default_factory=list)

    async def write_event(self, payload: TeachingPackEventCreate):
        self.written_events.append(payload)


def _lesson_sequence() -> JsonObject:
    sequence = LessonSequence(
        topic="Persisted event unit",
        grade_level="Grade 6",
        subject="Science",
        locale="en",
        total_sessions=1,
        total_duration_minutes=30,
        sessions=[
            SessionPlan(
                session_id="S01",
                order_index=1,
                title="Session one",
                sub_topic="Intro",
                duration_minutes=30,
                learning_objectives=["Understand the basics"],
                bloom_level_primary="understand",
                methodology_primary="concept_map",
                prerequisite_sessions=[],
            )
        ],
        grounding_status="grounded",
        confidence=0.9,
        rationale="Test fixture",
    )
    return sequence.model_dump()


class TestUnitOrchestratorEvents:
    async def test_spawn_writes_teacher_visible_persisted_progress_event(self) -> None:
        parent_run_id = RunId("unit-parent-events")
        parent_run = _ParentRun(
            teacher_id=TeacherId("teacher-events"),
            raw_request="Generate unit",
            class_info={"grade": 6, "subject": "Science"},
            retention_days=30,
        )
        session = _Session(parent_run=parent_run)
        unit_run_store = _UnitRunStore(lesson_sequence=_lesson_sequence())
        job_store = _JobStore()
        event_store = _EventStore(session=session)

        class _TeachingPackRunStore:
            def __new__(cls, _session):
                return event_store

        with patch("services.gateway.teaching_pack_store.TeachingPackRunStore", _TeachingPackRunStore):
            actions = await UnitOrchestrator(
                session=session,
                unit_run_store=unit_run_store,
                job_store=job_store,
            ).react(parent_run_id)

        spawns = [action for action in actions if action.action is OrchestratorAction.SPAWN]
        assert [action.session_id for action in spawns] == ["S01"]
        assert len(unit_run_store.created_children) == 1
        assert len(job_store.enqueued_jobs) == 1
        assert len(event_store.written_events) == 1

        event = event_store.written_events[0]
        assert event.run_id == parent_run_id
        assert event.event_name == "unit.session.spawned"
        assert event.visibility is TeachingPackEventVisibility.TEACHER
        assert event.payload is not None
        assert event.payload["event_type"] == "unit.progress"
        assert event.payload["parent_run_id"] == str(parent_run_id)
        assert event.payload["session_id"] == "S01"
        assert isinstance(event.payload["child_run_id"], str)
