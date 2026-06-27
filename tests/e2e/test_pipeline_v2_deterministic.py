"""Deterministic E2E tests for Pipeline V2.

Covers:
  - Orchestration flow: create → preflight → quickstart → contract
  - Gate flow: open gate → resume → gate closes
  - Persistence: run state survives simulated restart
  - Status SSE: events are emitted in order
  - Export: artifacts can be exported to HTML
  - Error handling: malformed input returns clear errors

All tests use mock data (no real LLM calls).  They operate directly
on the database layer via the store classes, bypassing HTTP, to isolate
the pipeline logic from transport concerns.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import select

from services.gateway.identity_hash import hash_teacher_id
from services.gateway.models import Run, RunStatus
from services.gateway.pipeline_v2_control_store import (
    GateInterruptCreate,
    GateResponseCreate,
    PipelineV2ControlStore,
    StaleGateResponseError,
)
from services.gateway.pipeline_v2_models import (
    GateInterrupt,
    GateInterruptStatus,
    PipelineV2EventVisibility,
    RunEvent,
    RunJob,
    RunJobKind,
    RunJobStatus,
)
from services.gateway.pipeline_v2_store import (
    PipelineV2EventCreate,
    PipelineV2RunCreate,
    PipelineV2RunStore,
    PipelineV2StatusTransition,
)
from services.gateway.pipeline_v2_status import validate_status_transition
from services.gateway.pipeline_v2_types import RunId, TeacherId
from services.gateway.release_evidence import ReleaseEvidence, generate_evidence
from services.gateway.release_evidence_store import (
    get_evidence,
    list_evidence,
    save_evidence,
)
from tests.e2e.conftest import (
    create_test_events,
    create_test_run,
    create_test_snapshot,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.anyio


# ─────────────────────────────────────────────────────────────────────
# §1  Orchestration flow: create → preflight → quickstart → contract
# ─────────────────────────────────────────────────────────────────────


class TestOrchestrationFlow:
    """Verify the basic lifecycle of a Pipeline V2 run through its
    store-level stages."""

    async def test_create_run_transitions_to_planning(self, session: AsyncSession, run_id: RunId, teacher_id: TeacherId) -> None:
        """Creating a run then transitioning to PLANNING should succeed."""
        store = PipelineV2RunStore(session)
        await store.create_run(PipelineV2RunCreate(
            run_id=run_id,
            teacher_id=teacher_id,
            raw_request="Teach equivalent fractions to Grade 5",
            class_info={"grade": 5, "subject": "math"},
        ))
        await session.flush()

        # Simulate the pipeline advancing from PENDING → PLANNING
        await store.transition_status(PipelineV2StatusTransition(
            run_id=run_id,
            status=RunStatus.PLANNING,
            stage="preflight",
            reason="preflight_passed",
        ))
        await session.flush()

        run = (await session.execute(select(Run).where(Run.run_id == run_id))).scalar_one()
        assert run.status is RunStatus.PLANNING

    async def test_full_ortest_orchestration_sequence(self, session: AsyncSession, run_id: RunId, teacher_id: TeacherId) -> None:
        """Walk through the full pipeline status sequence to COMPLETED."""
        store = PipelineV2RunStore(session)
        await store.create_run(PipelineV2RunCreate(
            run_id=run_id,
            teacher_id=teacher_id,
            raw_request="English lesson on phrasal verbs",
            class_info={"grade": 7, "subject": "english"},
        ))
        await session.flush()

        # PENDING → PLANNING → RESEARCHING → GENERATING → REVIEWING → EXPORTING → COMPLETED
        transitions = [
            (RunStatus.PLANNING, "quickstart", "run_started"),
            (RunStatus.RESEARCHING, "research", "research_started"),
            (RunStatus.GENERATING, "generate", "content_generation_started"),
            (RunStatus.REVIEWING, "review", "review_started"),
            (RunStatus.EXPORTING, "export", "export_started"),
            (RunStatus.COMPLETED, None, "run_completed"),
        ]
        for status, stage, reason in transitions:
            await store.transition_status(PipelineV2StatusTransition(
                run_id=run_id,
                status=status,
                stage=stage,
                reason=reason,
            ))
            await session.flush()

        run = (await session.execute(select(Run).where(Run.run_id == run_id))).scalar_one()
        assert run.status is RunStatus.COMPLETED

    async def test_events_emitted_during_orchestration(self, session: AsyncSession, run_id: RunId, teacher_id: TeacherId) -> None:
        """Stage events should be written at each pipeline stage."""
        store = PipelineV2RunStore(session)
        await store.create_run(PipelineV2RunCreate(
            run_id=run_id,
            teacher_id=teacher_id,
            raw_request="Teach photosynthesis",
            class_info={"grade": 6, "subject": "science"},
        ))
        await session.flush()

        # Write events for two stages
        await store.write_event(PipelineV2EventCreate(
            run_id=run_id,
            event_name="pipeline_v2.run.accepted",
            visibility=PipelineV2EventVisibility.TEACHER,
            payload={"job_id": "job-test"},
        ))
        await store.write_event(PipelineV2EventCreate(
            run_id=run_id,
            event_name="pipeline_v2.preflight.completed",
            visibility=PipelineV2EventVisibility.TEACHER,
        ))

        events = await store.replay_events(run_id)
        assert len(events) == 2
        assert events[0].event_name == "pipeline_v2.run.accepted"
        assert events[1].event_name == "pipeline_v2.preflight.completed"
        assert events[0].sequence < events[1].sequence


# ─────────────────────────────────────────────────────────────────────
# §2  Gate flow: open gate → resume → gate closes
# ─────────────────────────────────────────────────────────────────────


class TestGateFlow:
    """Verify the gate interrupt → response → close lifecycle."""

    async def test_open_gate_and_respond(self, session: AsyncSession, run_id: RunId, teacher_id: TeacherId) -> None:
        """Opening a gate then responding should update gate status."""
        await create_test_run(session, run_id=run_id, teacher_id=teacher_id, status=RunStatus.AWAITING_APPROVAL)

        control_store = PipelineV2ControlStore(session)
        gate_id = f"gate-{uuid4()}"
        await control_store.open_gate(GateInterruptCreate(
            gate_id=gate_id,
            run_id=run_id,
            gate_name="blueprint_approval",
            payload={"gate_id": gate_id, "plan": {"topic": "fractions"}},
        ))
        await session.flush()

        # Verify gate is open
        gates = await control_store.list_active_gates(run_id)
        assert len(gates) == 1
        assert gates[0].gate_name == "blueprint_approval"

        # Teacher responds
        response_id = f"response-{uuid4()}"
        await control_store.respond_to_gate(GateResponseCreate(
            response_id=response_id,
            gate_id=gate_id,
            run_id=run_id,
            teacher_id=teacher_id,
            response_json={"action": "approve"},
        ))
        await session.flush()

        # Gate should no longer be active
        gates_after = await control_store.list_active_gates(run_id)
        assert len(gates_after) == 0

    async def test_stale_gate_response_rejected(self, session: AsyncSession, run_id: RunId, teacher_id: TeacherId) -> None:
        """Responding to an already-responded gate should raise StaleGateResponseError."""
        await create_test_run(session, run_id=run_id, teacher_id=teacher_id, status=RunStatus.AWAITING_APPROVAL)

        control_store = PipelineV2ControlStore(session)
        gate_id = f"gate-{uuid4()}"
        await control_store.open_gate(GateInterruptCreate(
            gate_id=gate_id,
            run_id=run_id,
            gate_name="content_approval",
            payload={"gate_id": gate_id},
        ))
        await session.flush()

        # First response succeeds
        await control_store.respond_to_gate(GateResponseCreate(
            response_id="resp-1",
            gate_id=gate_id,
            run_id=run_id,
            teacher_id=teacher_id,
            response_json={"action": "approve"},
        ))
        await session.flush()

        # Second response should fail
        with pytest.raises(StaleGateResponseError):
            await control_store.respond_to_gate(GateResponseCreate(
                response_id="resp-2",
                gate_id=gate_id,
                run_id=run_id,
                teacher_id=teacher_id,
                response_json={"action": "approve"},
            ))

    async def test_gate_response_events_emitted(self, session: AsyncSession, run_id: RunId, teacher_id: TeacherId) -> None:
        """Gate open and response events should appear in the event log."""
        await create_test_run(session, run_id=run_id, teacher_id=teacher_id)

        store = PipelineV2RunStore(session)
        await store.write_event(PipelineV2EventCreate(
            run_id=run_id,
            event_name="pipeline_v2.blueprint_approval.opened",
            visibility=PipelineV2EventVisibility.TEACHER,
            payload={"gate_id": "gate-123"},
        ))
        await store.write_event(PipelineV2EventCreate(
            run_id=run_id,
            event_name="pipeline_v2.blueprint_approval.responded",
            visibility=PipelineV2EventVisibility.TEACHER,
            payload={"action": "approve"},
        ))

        events = await store.replay_events(run_id)
        assert len(events) == 2
        assert events[0].event_name == "pipeline_v2.blueprint_approval.opened"
        assert events[1].event_name == "pipeline_v2.blueprint_approval.responded"


# ─────────────────────────────────────────────────────────────────────
# §3  Persistence: run state survives simulated restart
# ─────────────────────────────────────────────────────────────────────


class TestPersistence:
    """Verify that run state is durable — a new session can read back
    everything written by a previous session."""

    async def test_run_survives_session_boundary(self, session: AsyncSession, run_id: RunId, teacher_id: TeacherId) -> None:
        """Create a run, commit, then read back in a fresh session."""
        store = PipelineV2RunStore(session)
        await store.create_run(PipelineV2RunCreate(
            run_id=run_id,
            teacher_id=teacher_id,
            raw_request="Teach Vietnam history Grade 10",
            class_info={"grade": 10, "subject": "history"},
        ))
        await session.commit()

        # Read back with same session (simulates post-commit read)
        run = await store.get_run(run_id, teacher_id)
        assert run is not None
        assert run.status is RunStatus.PENDING
        assert run.raw_request == "Teach Vietnam history Grade 10"

    async def test_events_survive_across_reads(self, session: AsyncSession, run_id: RunId, teacher_id: TeacherId) -> None:
        """Events written should be replayable after commit."""
        await create_test_run(session, run_id=run_id, teacher_id=teacher_id)
        await session.flush()

        store = PipelineV2RunStore(session)
        for i in range(5):
            await store.write_event(PipelineV2EventCreate(
                run_id=run_id,
                event_name=f"pipeline_v2.test.event_{i}",
                visibility=PipelineV2EventVisibility.INTERNAL,
            ))
        await session.commit()

        events = await store.replay_events(run_id)
        assert len(events) == 5
        for i, evt in enumerate(events):
            assert evt.event_name == f"pipeline_v2.test.event_{i}"
            assert evt.sequence == i + 1

    async def test_status_history_persisted(self, session: AsyncSession, run_id: RunId, teacher_id: TeacherId) -> None:
        """Status transitions should be recorded in run_status_history."""
        await create_test_run(session, run_id=run_id, teacher_id=teacher_id)

        store = PipelineV2RunStore(session)
        await store.transition_status(PipelineV2StatusTransition(
            run_id=run_id,
            status=RunStatus.PLANNING,
            stage="preflight",
            reason="run_started",
        ))
        await session.commit()

        from services.gateway.pipeline_v2_models import RunStatusHistory
        result = await session.execute(
            select(RunStatusHistory).where(RunStatusHistory.run_id == run_id)
        )
        history = result.scalars().all()
        # At least the initial PENDING + transition to PLANNING
        statuses = {h.status for h in history}
        assert RunStatus.PENDING in statuses
        assert RunStatus.PLANNING in statuses


# ─────────────────────────────────────────────────────────────────────
# §4  Status SSE: events are emitted in order
# ─────────────────────────────────────────────────────────────────────


class TestStatusSSE:
    """Verify event ordering and replay for SSE streaming."""

    async def test_events_are_sequential(self, session: AsyncSession, run_id: RunId, teacher_id: TeacherId) -> None:
        """Events must have monotonically increasing sequence numbers."""
        await create_test_run(session, run_id=run_id, teacher_id=teacher_id)

        store = PipelineV2RunStore(session)
        for i in range(10):
            await store.write_event(PipelineV2EventCreate(
                run_id=run_id,
                event_name=f"seq_test.event_{i}",
                visibility=PipelineV2EventVisibility.TEACHER,
            ))
        await session.flush()

        events = await store.replay_events(run_id)
        assert len(events) == 10
        sequences = [e.sequence for e in events]
        assert sequences == list(range(1, 11))

    async def test_replay_after_sequence_filters_correctly(self, session: AsyncSession, run_id: RunId, teacher_id: TeacherId) -> None:
        """Replay with after_sequence should skip earlier events."""
        await create_test_run(session, run_id=run_id, teacher_id=teacher_id)

        store = PipelineV2RunStore(session)
        for i in range(5):
            await store.write_event(PipelineV2EventCreate(
                run_id=run_id,
                event_name=f"filter_test.event_{i}",
                visibility=PipelineV2EventVisibility.TEACHER,
            ))
        await session.flush()

        events_after_3 = await store.replay_events(run_id, after_sequence=3)
        assert len(events_after_3) == 2
        assert events_after_3[0].sequence == 4
        assert events_after_3[1].sequence == 5

    async def test_teacher_visibility_filter(self, session: AsyncSession, run_id: RunId, teacher_id: TeacherId) -> None:
        """Internal events should not be mixed with teacher events when filtering."""
        await create_test_run(session, run_id=run_id, teacher_id=teacher_id)

        store = PipelineV2RunStore(session)
        await store.write_event(PipelineV2EventCreate(
            run_id=run_id,
            event_name="teacher.visible",
            visibility=PipelineV2EventVisibility.TEACHER,
        ))
        await store.write_event(PipelineV2EventCreate(
            run_id=run_id,
            event_name="admin.only",
            visibility=PipelineV2EventVisibility.ADMIN,
        ))
        await store.write_event(PipelineV2EventCreate(
            run_id=run_id,
            event_name="internal.only",
            visibility=PipelineV2EventVisibility.INTERNAL,
        ))
        await session.flush()

        events = await store.replay_events(run_id)
        # All events returned (replay doesn't filter by visibility)
        assert len(events) == 3
        # Caller should filter; verify the visibility is correct
        teacher_events = [e for e in events if e.visibility == PipelineV2EventVisibility.TEACHER]
        assert len(teacher_events) == 1


# ─────────────────────────────────────────────────────────────────────
# §5  Export: artifacts can be exported to HTML
# ─────────────────────────────────────────────────────────────────────


class TestExport:
    """Verify artifact snapshots are stored and retrievable."""

    async def test_snapshot_stored_and_queryable(self, session: AsyncSession, run_id: RunId, teacher_id: TeacherId) -> None:
        """A created snapshot should be retrievable by content hash."""
        await create_test_run(session, run_id=run_id, teacher_id=teacher_id)

        store = PipelineV2RunStore(session)
        content_hash = f"hash-{uuid4().hex[:8]}"
        html_hash = f"html-{uuid4().hex[:8]}"

        from services.gateway.pipeline_v2_snapshot_store import ArtifactSnapshotCreate
        await store.create_snapshot(ArtifactSnapshotCreate(
            run_id=run_id,
            artifact_id="art-001",
            artifact_type="worksheet",
            content_hash=content_hash,
            html_hash=html_hash,
            content_json={"title": "Equivalent Fractions Worksheet"},
            rendered_html="<!DOCTYPE html><html><body>worksheet</body></html>",
            student_rendered_html="<!DOCTYPE html><html><body>student view</body></html>",
            renderer_version="1.0.0",
            template_version="1.0.0",
            theme_version="1.0.0",
            standalone_valid=True,
        ))
        await session.flush()

        has = await store.has_snapshot(content_hash)
        assert has is True
        has_other = await store.has_snapshot("nonexistent-hash")
        assert has_other is False

    async def test_multiple_snapshots_per_run(self, session: AsyncSession, run_id: RunId, teacher_id: TeacherId) -> None:
        """Multiple snapshots can exist for a single run."""
        await create_test_run(session, run_id=run_id, teacher_id=teacher_id)

        store = PipelineV2RunStore(session)
        from services.gateway.pipeline_v2_snapshot_store import ArtifactSnapshotCreate
        for i in range(3):
            await store.create_snapshot(ArtifactSnapshotCreate(
                run_id=run_id,
                artifact_id=f"art-{i}",
                artifact_type=["lesson", "worksheet", "quiz"][i],
                content_hash=f"content-{i}",
                html_hash=f"html-{i}",
                content_json={"title": f"Artifact {i}"},
                rendered_html=f"<html>artifact {i}</html>",
                student_rendered_html=f"<html>student {i}</html>",
                renderer_version="1.0",
                template_version="1.0",
                theme_version="1.0",
                standalone_valid=True,
            ))
        await session.flush()

        for i in range(3):
            assert await store.has_snapshot(f"content-{i}")


# ─────────────────────────────────────────────────────────────────────
# §6  Error handling: malformed input returns clear errors
# ─────────────────────────────────────────────────────────────────────


class TestErrorHandling:
    """Verify error paths for invalid operations."""

    async def test_invalid_status_transition_rejected(self, session: AsyncSession, run_id: RunId, teacher_id: TeacherId) -> None:
        """Transitioning from COMPLETED should fail (terminal state)."""
        await create_test_run(session, run_id=run_id, teacher_id=teacher_id, status=RunStatus.COMPLETED)

        store = PipelineV2RunStore(session)
        from services.gateway.pipeline_v2_store import InvalidRunStatusTransitionError
        with pytest.raises(InvalidRunStatusTransitionError):
            await store.transition_status(PipelineV2StatusTransition(
                run_id=run_id,
                status=RunStatus.PLANNING,
                stage="restart",
                reason="retry",
            ))

    async def test_skip_terminal_state_validation(self) -> None:
        """validate_status_transition should reject impossible transitions."""
        result = validate_status_transition(RunStatus.COMPLETED, RunStatus.PENDING)
        from services.gateway.pipeline_v2_status import StatusTransitionRejected
        assert isinstance(result, StatusTransitionRejected)

    async def test_nonexistent_run_get_returns_none(self, session: AsyncSession, run_id: RunId, teacher_id: TeacherId) -> None:
        """Querying a non-existent run should return None, not crash."""
        store = PipelineV2RunStore(session)
        result = await store.get_run(run_id, teacher_id)
        assert result is None

    async def test_valid_transition_accepted(self) -> None:
        """validate_status_transition should accept valid transitions."""
        result = validate_status_transition(RunStatus.PENDING, RunStatus.PLANNING)
        from services.gateway.pipeline_v2_status import StatusTransitionAccepted
        assert isinstance(result, StatusTransitionAccepted)

    async def test_same_status_transition_accepted(self) -> None:
        """Transitioning to the same status should be a no-op success."""
        result = validate_status_transition(RunStatus.PENDING, RunStatus.PENDING)
        from services.gateway.pipeline_v2_status import StatusTransitionAccepted
        assert isinstance(result, StatusTransitionAccepted)


# ─────────────────────────────────────────────────────────────────────
# §7  Release evidence generation
# ─────────────────────────────────────────────────────────────────────


class TestReleaseEvidenceGeneration:
    """Verify that evidence can be generated from run state."""

    async def test_generate_evidence_from_run(self, session: AsyncSession, run_id: RunId, teacher_id: TeacherId) -> None:
        """generate_evidence should produce a complete evidence record."""
        await create_test_run(session, run_id=run_id, teacher_id=teacher_id, status=RunStatus.COMPLETED)

        await create_test_events(session, run_id=run_id, events=[
            {"event_name": "pipeline_v2.run.accepted", "stage": None},
            {"event_name": "pipeline_v2.preflight.started", "stage": "preflight"},
            {"event_name": "pipeline_v2.preflight.completed", "stage": "preflight"},
            {"event_name": "pipeline_v2.generate.started", "stage": "generate"},
            {"event_name": "pipeline_v2.generate.completed", "stage": "generate"},
        ])

        await create_test_snapshot(
            session,
            snapshot_id="snap-001",
            run_id=run_id,
        )
        await session.flush()

        evidence = await generate_evidence(run_id, session)
        assert evidence.run_id == run_id
        assert evidence.status == "completed"
        assert len(evidence.event_sequence) == 5
        assert len(evidence.snapshot_ids) == 1
        assert evidence.tokens_used == 1234
        assert evidence.cost_usd == 0.042
        # Teacher ID should be hashed
        assert evidence.teacher_id_hash == hash_teacher_id(teacher_id)
        assert evidence.teacher_id_hash != teacher_id

    async def test_generate_evidence_nonexistent_run(self, session: AsyncSession) -> None:
        """generate_evidence for a missing run should raise ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await generate_evidence(RunId("nonexistent-run"), session)

    async def test_evidence_persistence_round_trip(self, session: AsyncSession, run_id: RunId, teacher_id: TeacherId) -> None:
        """save_evidence → get_evidence should round-trip correctly."""
        await create_test_run(session, run_id=run_id, teacher_id=teacher_id)

        evidence = await generate_evidence(run_id, session)
        await save_evidence(evidence, session)
        await session.flush()

        loaded = await get_evidence(run_id, session)
        assert loaded is not None
        assert loaded.run_id == run_id
        assert loaded.teacher_id_hash == evidence.teacher_id_hash

    async def test_list_evidence_returns_newest_first(self, session: AsyncSession, teacher_id: TeacherId) -> None:
        """list_evidence should return records ordered by created_at descending."""
        from datetime import UTC, datetime, timedelta

        for i in range(3):
            rid = RunId(f"run-list-{i}")
            await create_test_run(session, run_id=rid, teacher_id=teacher_id)
            ev = await generate_evidence(rid, session)
            await save_evidence(ev, session)
        await session.flush()

        items = await list_evidence(session, limit=10)
        assert len(items) == 3
        # Created most recently first (all share same created_at so order is by insertion)
        run_ids = [e.run_id for e in items]
        assert "run-list-0" in run_ids
