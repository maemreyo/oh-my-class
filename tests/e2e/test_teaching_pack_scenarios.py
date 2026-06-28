"""E2E scenarios for Teaching Pack — real-world use cases.

Each scenario exercises the full pipeline through the store layer,
with mock data standing in for LLM output.  No real API calls are made.

Scenarios:
  1. Vietnamese Grade 5 Math (equivalent fractions)
  2. English Grade 7 (phrasal verbs)
  3. Missing grade/subject triggers clarification
  4. Content approval with scoped rejection
  5. Run cancellation
  6. Schema version validation
  7. Soft-delete and restore
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import select

from services.gateway.identity_hash import hash_teacher_id
from services.gateway.models import Run, RunStatus
from services.gateway.teaching_pack_control_store import (
    GateInterruptCreate,
    GateResponseCreate,
    TeachingPackControlStore,
)
from services.gateway.teaching_pack_models import (
    ArtifactSnapshot,
    TeachingPackEventVisibility,
)
from services.gateway.teaching_pack_snapshot_store import ArtifactSnapshotCreate
from services.gateway.teaching_pack_store import (
    TeachingPackEventCreate,
    TeachingPackRunCreate,
    TeachingPackRunStore,
    TeachingPackStatusTransition,
)
from services.gateway.teaching_pack_types import RunId, TeacherId
from services.gateway.release_evidence import generate_evidence
from services.gateway.release_evidence_store import save_evidence
from services.gateway.schema_version import (
    SCHEMA_VERSION,
    SUPPORTED_VERSIONS,
    migrate_contract,
    validate_schema_version,
)
from services.gateway.soft_delete import is_run_deleted, restore_run, soft_delete_run
from tests.e2e.conftest import (
    create_test_events,
    create_test_run,
    create_test_snapshot,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.anyio


# ─────────────────────────────────────────────────────────────────────
# Scenario 1: Vietnamese Grade 5 Math — Equivalent Fractions
# ─────────────────────────────────────────────────────────────────────


class TestScenarioVietnameseGrade5Math:
    """Full pipeline run for a Vietnamese Grade 5 math lesson."""

    async def test_equivalent_fractions_full_lifecycle(self, session: AsyncSession) -> None:
        run_id = RunId(f"run-vn-math-{uuid4()}")
        teacher_id = TeacherId("teacher-vn-001")

        store = TeachingPackRunStore(session)

        # ── Step 1: Create run (preflight) ──────────────────────────
        await store.create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=teacher_id,
            raw_request="Dạy phân số tương đương cho lớp 5",
            class_info={
                "grade": 5,
                "subject": "math",
                "language": "vi",
                "student_count": 35,
            },
        ))
        await session.flush()

        # ── Step 2: Contract confirmation gate ──────────────────────
        control_store = TeachingPackControlStore(session)
        gate_id = f"gate-cn-{uuid4()}"
        await control_store.open_gate(GateInterruptCreate(
            gate_id=gate_id,
            run_id=run_id,
            gate_name="contract_confirmation",
            payload={
                "gate_id": gate_id,
                "contract": {
                    "topic": "Phân số tương đương",
                    "grade_band": "Grade 5",
                    "subject": "math",
                    "locale": "vi",
                    "artifact_types": ["lesson", "worksheet", "quiz"],
                },
            },
        ))
        await store.transition_status(TeachingPackStatusTransition(
            run_id=run_id,
            status=RunStatus.AWAITING_APPROVAL,
            stage="setup_contract",
            reason="contract_confirmation",
        ))
        await store.write_event(TeachingPackEventCreate(
            run_id=run_id,
            event_name="teaching_pack.contract_confirmation.opened",
            visibility=TeachingPackEventVisibility.TEACHER,
            payload={"gate_id": gate_id},
        ))
        await session.flush()

        # Teacher approves contract
        await control_store.respond_to_gate(GateResponseCreate(
            response_id=f"resp-{uuid4()}",
            gate_id=gate_id,
            run_id=run_id,
            teacher_id=teacher_id,
            response_json={"action": "approve"},
        ))
        await store.transition_status(TeachingPackStatusTransition(
            run_id=run_id,
            status=RunStatus.PLANNING,
            stage="contract_approved",
            reason="teacher_approved",
        ))
        await store.write_event(TeachingPackEventCreate(
            run_id=run_id,
            event_name="teaching_pack.contract_confirmation.responded",
            visibility=TeachingPackEventVisibility.TEACHER,
            payload={"action": "approve"},
        ))
        await session.flush()

        # ── Step 3: Pipeline runs through stages ────────────────────
        stages = [
            (RunStatus.PLANNING, "planning", "planning_started"),
            (RunStatus.RESEARCHING, "research", "research_started"),
            (RunStatus.GENERATING, "generate", "generation_started"),
            (RunStatus.REVIEWING, "review", "review_started"),
        ]
        for status, stage, reason in stages:
            await store.transition_status(TeachingPackStatusTransition(
                run_id=run_id, status=status, stage=stage, reason=reason,
            ))
        await session.flush()

        # ── Step 4: Content approval gate ───────────────────────────
        snapshot_id = f"snap-vn-math-{uuid4()}"
        await create_test_snapshot(
            session, snapshot_id=snapshot_id, run_id=run_id,
            artifact_id="art-lesson-1",
        )
        content_gate_id = f"gate-content-{uuid4()}"
        await control_store.open_gate(GateInterruptCreate(
            gate_id=content_gate_id,
            run_id=run_id,
            gate_name="content_approval",
            payload={
                "gate_id": content_gate_id,
                "snapshot_ids": [snapshot_id],
                "artifacts": [{"artifact_id": "art-lesson-1", "artifact_type": "lesson"}],
            },
        ))
        await store.transition_status(TeachingPackStatusTransition(
            run_id=run_id,
            status=RunStatus.AWAITING_APPROVAL,
            stage="content_approval",
            reason="content_approval",
        ))
        await session.flush()

        # Teacher approves content
        await control_store.respond_to_gate(GateResponseCreate(
            response_id=f"resp-{uuid4()}",
            gate_id=content_gate_id,
            run_id=run_id,
            teacher_id=teacher_id,
            response_json={"action": "approve"},
        ))
        await session.flush()

        # ── Step 5: Export & Complete ───────────────────────────────
        await store.transition_status(TeachingPackStatusTransition(
            run_id=run_id, status=RunStatus.EXPORTING, stage="export", reason="exporting",
        ))
        await store.transition_status(TeachingPackStatusTransition(
            run_id=run_id, status=RunStatus.COMPLETED, stage=None, reason="completed",
        ))
        await session.flush()

        # ── Verify ─────────────────────────────────────────────────
        run = (await session.execute(select(Run).where(Run.run_id == run_id))).scalar_one()
        assert run.status is RunStatus.COMPLETED
        assert run.raw_request == "Dạy phân số tương đương cho lớp 5"

        events = await store.replay_events(run_id)
        assert len(events) >= 5  # At least contract + content gates + stage transitions

        # Verify evidence generation
        evidence = await generate_evidence(run_id, session)
        assert evidence.status == "completed"
        assert evidence.teacher_id_hash == hash_teacher_id(teacher_id)


# ─────────────────────────────────────────────────────────────────────
# Scenario 2: English Grade 7 — Phrasal Verbs
# ─────────────────────────────────────────────────────────────────────


class TestScenarioEnglishGrade7PhrasalVerbs:
    """Pipeline run for an English language lesson on phrasal verbs."""

    async def test_phasal_verbs_full_lifecycle(self, session: AsyncSession) -> None:
        run_id = RunId(f"run-en-phrasal-{uuid4()}")
        teacher_id = TeacherId("teacher-en-002")

        store = TeachingPackRunStore(session)
        await store.create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=teacher_id,
            raw_request="Teach common phrasal verbs to Grade 7",
            class_info={
                "grade": 7,
                "subject": "english",
                "student_count": 28,
            },
        ))
        await session.flush()

        # Full pipeline walk
        transitions = [
            (RunStatus.PLANNING, "quickstart", "started"),
            (RunStatus.RESEARCHING, "research", "research_started"),
            (RunStatus.GENERATING, "generate", "generate_started"),
            (RunStatus.REVIEWING, "review", "review_started"),
            (RunStatus.EXPORTING, "export", "export_started"),
            (RunStatus.COMPLETED, None, "completed"),
        ]
        for status, stage, reason in transitions:
            await store.transition_status(TeachingPackStatusTransition(
                run_id=run_id, status=status, stage=stage, reason=reason,
            ))
        await session.flush()

        run = (await session.execute(select(Run).where(Run.run_id == run_id))).scalar_one()
        assert run.status is RunStatus.COMPLETED

        # Verify evidence
        evidence = await generate_evidence(run_id, session)
        assert evidence.run_id == run_id
        assert evidence.status == "completed"


# ─────────────────────────────────────────────────────────────────────
# Scenario 3: Missing grade/subject triggers clarification
# ─────────────────────────────────────────────────────────────────────


class TestScenarioClarification:
    """When the teacher's request is missing grade/subject, a
    clarification_required gate should be opened."""

    async def test_missing_class_info_opens_clarification_gate(self, session: AsyncSession) -> None:
        run_id = RunId(f"run-clarity-{uuid4()}")
        teacher_id = TeacherId("teacher-clarity-003")

        store = TeachingPackRunStore(session)
        await store.create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=teacher_id,
            raw_request="Teach something about science",
            class_info={},  # Missing grade and subject
        ))
        await session.flush()

        control_store = TeachingPackControlStore(session)
        gate_id = f"gate-clarity-{uuid4()}"
        await control_store.open_gate(GateInterruptCreate(
            gate_id=gate_id,
            run_id=run_id,
            gate_name="clarification_required",
            payload={
                "gate_id": gate_id,
                "questions": [
                    {"field": "grade", "prompt": "What grade level?"},
                    {"field": "subject", "prompt": "Which subject?"},
                ],
            },
        ))
        await store.transition_status(TeachingPackStatusTransition(
            run_id=run_id,
            status=RunStatus.AWAITING_APPROVAL,
            stage="setup_clarification",
            reason="clarification_required",
        ))
        await session.flush()

        gates = await control_store.list_active_gates(run_id)
        assert len(gates) == 1
        assert gates[0].gate_name == "clarification_required"

        # Teacher responds with clarification
        await control_store.respond_to_gate(GateResponseCreate(
            response_id=f"resp-{uuid4()}",
            gate_id=gate_id,
            run_id=run_id,
            teacher_id=teacher_id,
            response_json={
                "action": "respond",
                "grade": 5,
                "subject": "science",
            },
        ))
        await session.flush()

        gates_after = await control_store.list_active_gates(run_id)
        assert len(gates_after) == 0


# ─────────────────────────────────────────────────────────────────────
# Scenario 4: Content approval with scoped rejection
# ─────────────────────────────────────────────────────────────────────


class TestScenarioScopedRejection:
    """Teacher can reject specific artifacts while approving others."""

    async def test_scoped_rejection_partial(self, session: AsyncSession) -> None:
        run_id = RunId(f"run-scoped-{uuid4()}")
        teacher_id = TeacherId("teacher-scoped-004")

        store = TeachingPackRunStore(session)
        await create_test_run(session, run_id=run_id, teacher_id=teacher_id, status=RunStatus.AWAITING_APPROVAL)

        # Create two snapshots
        snap1 = f"snap-a-{uuid4()}"
        snap2 = f"snap-b-{uuid4()}"
        await create_test_snapshot(session, snapshot_id=snap1, run_id=run_id, artifact_id="art-worksheet")
        await create_test_snapshot(session, snapshot_id=snap2, run_id=run_id, artifact_id="art-quiz")

        control_store = TeachingPackControlStore(session)
        gate_id = f"gate-scoped-{uuid4()}"
        await control_store.open_gate(GateInterruptCreate(
            gate_id=gate_id,
            run_id=run_id,
            gate_name="content_approval",
            payload={
                "gate_id": gate_id,
                "snapshot_ids": [snap1, snap2],
                "artifacts": [
                    {"artifact_id": "art-worksheet", "artifact_type": "worksheet"},
                    {"artifact_id": "art-quiz", "artifact_type": "quiz"},
                ],
            },
        ))
        await session.flush()

        # Teacher rejects only the quiz artifact
        await control_store.respond_to_gate(GateResponseCreate(
            response_id=f"resp-{uuid4()}",
            gate_id=gate_id,
            run_id=run_id,
            teacher_id=teacher_id,
            response_json={
                "action": "reject",
                "rejection_type": "scoped",
                "artifact_rejections": [
                    {
                        "artifact_id": "art-quiz",
                        "reason": "Too many questions",
                    },
                ],
            },
        ))
        await session.flush()

        gates_after = await control_store.list_active_gates(run_id)
        assert len(gates_after) == 0


# ─────────────────────────────────────────────────────────────────────
# Scenario 5: Run cancellation
# ─────────────────────────────────────────────────────────────────────


class TestScenarioRunCancellation:
    """Teacher cancels a running pipeline."""

    async def test_cancel_planning_run(self, session: AsyncSession) -> None:
        run_id = RunId(f"run-cancel-{uuid4()}")
        teacher_id = TeacherId("teacher-cancel-005")

        store = TeachingPackRunStore(session)
        await create_test_run(session, run_id=run_id, teacher_id=teacher_id, status=RunStatus.PLANNING)

        await store.transition_status(TeachingPackStatusTransition(
            run_id=run_id,
            status=RunStatus.CANCELLED,
            stage=None,
            reason="teacher_cancelled",
        ))
        await store.write_event(TeachingPackEventCreate(
            run_id=run_id,
            event_name="teaching_pack.run.cancelled",
            visibility=TeachingPackEventVisibility.TEACHER,
            payload={"cancelled_jobs": 1},
        ))
        await session.flush()

        run = (await session.execute(select(Run).where(Run.run_id == run_id))).scalar_one()
        assert run.status is RunStatus.CANCELLED

        events = await store.replay_events(run_id)
        cancel_events = [e for e in events if "cancelled" in e.event_name]
        assert len(cancel_events) == 1

    async def test_cancel_researching_run(self, session: AsyncSession) -> None:
        """Cancelling from RESEARCHING state."""
        run_id = RunId(f"run-cancel-res-{uuid4()}")
        teacher_id = TeacherId("teacher-cancel-006")

        store = TeachingPackRunStore(session)
        await create_test_run(session, run_id=run_id, teacher_id=teacher_id, status=RunStatus.RESEARCHING)

        await store.transition_status(TeachingPackStatusTransition(
            run_id=run_id,
            status=RunStatus.CANCELLED,
            stage=None,
            reason="teacher_cancelled",
        ))
        await session.flush()

        run = (await session.execute(select(Run).where(Run.run_id == run_id))).scalar_one()
        assert run.status is RunStatus.CANCELLED


# ─────────────────────────────────────────────────────────────────────
# Scenario 6: Schema version validation
# ─────────────────────────────────────────────────────────────────────


class TestScenarioSchemaVersion:
    """Verify schema version handling for pipeline contracts."""

    def test_current_version_is_valid(self) -> None:
        assert validate_schema_version(SCHEMA_VERSION) is True

    def test_supported_versions_are_all_valid(self) -> None:
        for version in SUPPORTED_VERSIONS:
            assert validate_schema_version(version) is True

    def test_unknown_version_is_rejected(self) -> None:
        assert validate_schema_version("99.0") is False
        assert validate_schema_version("invalid") is False
        assert validate_schema_version("") is False

    def test_migrate_same_version_is_noop(self) -> None:
        data = {"topic": "fractions", "schema_version": "1.0"}
        migrated = migrate_contract(data, from_version="1.0", to_version="1.0")
        assert migrated == data

    def test_migrate_rejects_unsupported_source(self) -> None:
        with pytest.raises(ValueError, match="Unsupported source version"):
            migrate_contract({}, from_version="0.5", to_version="1.0")

    def test_migrate_rejects_unsupported_target(self) -> None:
        with pytest.raises(ValueError, match="Unsupported target version"):
            migrate_contract({}, from_version="1.0", to_version="99.0")


# ─────────────────────────────────────────────────────────────────────
# Scenario 7: Soft-delete and restore
# ─────────────────────────────────────────────────────────────────────


class TestScenarioSoftDeleteRestore:
    """Soft-deleting and restoring a run should preserve all data."""

    async def test_soft_delete_hides_from_normal_queries(self, session: AsyncSession) -> None:
        run_id = RunId(f"run-del-{uuid4()}")
        teacher_id = TeacherId("teacher-del-007")

        await create_test_run(session, run_id=run_id, teacher_id=teacher_id)

        # Soft-delete
        await soft_delete_run(run_id, "teacher-del-007", session)
        await session.flush()

        is_deleted = await is_run_deleted(run_id, session)
        assert is_deleted is True

        # Row still exists in DB
        run = (await session.execute(select(Run).where(Run.run_id == run_id))).scalar_one()
        assert run.deleted_at is not None

    async def test_restore_makes_visible_again(self, session: AsyncSession) -> None:
        run_id = RunId(f"run-restore-{uuid4()}")
        teacher_id = TeacherId("teacher-restore-008")

        await create_test_run(session, run_id=run_id, teacher_id=teacher_id)

        await soft_delete_run(run_id, teacher_id, session)
        await session.flush()

        assert await is_run_deleted(run_id, session) is True

        # Restore
        await restore_run(run_id, teacher_id, session)
        await session.flush()

        assert await is_run_deleted(run_id, session) is False

    async def test_events_preserved_through_delete_restore(self, session: AsyncSession) -> None:
        """Events should not be lost during soft-delete/restore."""
        run_id = RunId(f"run-del-events-{uuid4()}")
        teacher_id = TeacherId("teacher-del-events-009")

        await create_test_run(session, run_id=run_id, teacher_id=teacher_id)

        store = TeachingPackRunStore(session)
        await store.write_event(TeachingPackEventCreate(
            run_id=run_id,
            event_name="teaching_pack.run.accepted",
            visibility=TeachingPackEventVisibility.TEACHER,
        ))
        await session.flush()

        # Soft-delete
        await soft_delete_run(run_id, teacher_id, session)
        await session.flush()

        # Restore
        await restore_run(run_id, teacher_id, session)
        await session.flush()

        events = await store.replay_events(run_id)
        assert len(events) == 3
        assert events[0].event_name == "teaching_pack.run.accepted"
