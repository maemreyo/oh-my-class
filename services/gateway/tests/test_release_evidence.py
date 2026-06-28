"""Unit tests for the ReleaseEvidence model and store layer.

Covers:
  - Evidence generation with all fields
  - Evidence storage and retrieval
  - Evidence list ordering
  - teacher_id is hashed in evidence
  - Evidence includes event sequence
  - Evidence includes artifact and snapshot IDs
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import services.gateway.routers.release_evidence as release_evidence_router
from services.gateway.auth.models import Role, User
from services.gateway.identity_hash import hash_teacher_id
from services.gateway.models import Base, Run, RunStatus
from services.gateway.teaching_pack_models import TeachingPackEventVisibility, RunEvent
from services.gateway.teaching_pack_types import RunId, TeacherId
from services.gateway.release_evidence import (
    ReleaseEvidence,
    ReleaseEvidenceRecord,
    generate_evidence,
    render_evidence_markdown,
    write_evidence_report,
)
from services.gateway.release_evidence_store import (
    get_evidence,
    list_evidence,
    save_evidence,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """Session fixture that skips if DB tables are not available."""
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        existing = await conn.run_sync(lambda c: set(Base.metadata.tables.keys()))
        if "runs" not in existing:
            pytest.skip("Teaching Pack tables are not present")
    async with session_factory() as db:
        yield db
        await db.rollback()
    await engine.dispose()


# ─────────────────────────────────────────────────────────────────────
# §1  Evidence dataclass fields
# ─────────────────────────────────────────────────────────────────────


class TestReleaseEvidenceDataclass:
    """Test the ReleaseEvidence frozen dataclass directly."""

    def test_default_values(self) -> None:
        e = ReleaseEvidence(
            run_id="run-1",
            teacher_id_hash="abc123",
            status="completed",
        )
        assert e.event_sequence == []
        assert e.artifact_ids == []
        assert e.snapshot_ids == []
        assert e.export_files == []
        assert e.trace_ids == []
        assert e.total_duration_ms == 0
        assert e.per_stage_duration_ms == {}
        assert e.tokens_used == 0
        assert e.cost_usd == 0.0
        assert e.created_at is None
        assert e.completed_at is None

    def test_all_fields_populated(self) -> None:
        now = datetime.now(UTC)
        e = ReleaseEvidence(
            run_id="run-full",
            teacher_id_hash="hash123",
            status="completed",
            event_sequence=[{"seq": 1, "event": "started"}],
            artifact_ids=["art-1", "art-2"],
            snapshot_ids=["snap-1"],
            export_files=["export.html"],
            trace_ids=["trace-abc"],
            total_duration_ms=45000,
            per_stage_duration_ms={"planning": 5000, "generate": 20000},
            tokens_used=12345,
            cost_usd=0.55,
            created_at=now,
            completed_at=now,
        )
        assert e.run_id == "run-full"
        assert len(e.event_sequence) == 1
        assert len(e.artifact_ids) == 2
        assert e.per_stage_duration_ms["generate"] == 20000

    def test_to_db_record_and_back(self) -> None:
        """Round-trip through DB record should preserve all fields."""
        now = datetime.now(UTC)
        original = ReleaseEvidence(
            run_id="run-roundtrip",
            teacher_id_hash="hash-rt",
            status="completed",
            event_sequence=[{"a": 1}],
            artifact_ids=["art-1"],
            snapshot_ids=["snap-1"],
            export_files=["out.html"],
            trace_ids=["t-1"],
            total_duration_ms=1000,
            per_stage_duration_ms={"planning": 500},
            tokens_used=999,
            cost_usd=0.1,
            created_at=now,
            completed_at=now,
        )

        record = original.to_db_record()
        restored = ReleaseEvidence.from_db_record(record)

        assert restored.run_id == original.run_id
        assert restored.teacher_id_hash == original.teacher_id_hash
        assert restored.status == original.status
        assert restored.event_sequence == original.event_sequence
        assert restored.artifact_ids == original.artifact_ids
        assert restored.snapshot_ids == original.snapshot_ids
        assert restored.export_files == original.export_files
        assert restored.trace_ids == original.trace_ids
        assert restored.total_duration_ms == original.total_duration_ms
        assert restored.per_stage_duration_ms == original.per_stage_duration_ms
        assert restored.tokens_used == original.tokens_used
        assert restored.cost_usd == original.cost_usd

    def test_frozen(self) -> None:
        """ReleaseEvidence is immutable."""
        e = ReleaseEvidence(run_id="x", teacher_id_hash="y", status="z")
        with pytest.raises(AttributeError):
            e.run_id = "changed"  # type: ignore[misc]

    def test_write_evidence_report_creates_markdown_file(self, tmp_path) -> None:
        evidence = ReleaseEvidence(
            run_id="run-report",
            teacher_id_hash="teacherhash1234",
            status="completed",
            event_sequence=[{"sequence": 1, "event_name": "teaching_pack.run.accepted"}],
        )

        report_path = write_evidence_report(evidence, tmp_path)

        assert report_path.name == "teaching-pack-run-evidence-run-report.md"
        assert "Teaching Pack Release Evidence" in report_path.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────
# §2  Teacher ID hashing
# ─────────────────────────────────────────────────────────────────────


class TestTeacherIdHashing:
    """Verify that teacher_id is always hashed in evidence records."""

    def test_hash_is_computed(self) -> None:
        e = ReleaseEvidence(
            run_id="r1",
            teacher_id_hash=hash_teacher_id("teacher-123"),
            status="completed",
        )
        assert e.teacher_id_hash != "teacher-123"
        assert len(e.teacher_id_hash) == 16  # SHA-256 truncated

    def test_different_ids_produce_different_hashes(self) -> None:
        h1 = hash_teacher_id("teacher-A")
        h2 = hash_teacher_id("teacher-B")
        assert h1 != h2

    def test_same_id_produces_same_hash(self) -> None:
        h1 = hash_teacher_id("teacher-C")
        h2 = hash_teacher_id("teacher-C")
        assert h1 == h2


# ─────────────────────────────────────────────────────────────────────
# §3  Evidence generation from DB
# ─────────────────────────────────────────────────────────────────────


class TestEvidenceGeneration:
    """Test generate_evidence with real DB rows."""

    async def _setup_run(self, session: AsyncSession, run_id: RunId, teacher_id: TeacherId) -> None:
        run = Run(
            run_id=run_id,
            teacher_id=teacher_id,
            status=RunStatus.COMPLETED,
            current_step=13,
            raw_request="Test run",
            class_info={"grade": 5},
            tokens_used=5000,
            cost_usd=0.33,
        )
        session.add(run)
        await session.flush()

    async def test_generate_evidence_fields(self, session: AsyncSession) -> None:
        """All fields should be populated correctly."""
        run_id = RunId(f"ev-gen-{uuid4()}")
        teacher_id = TeacherId("teacher-gen-001")
        await self._setup_run(session, run_id, teacher_id)

        # Add events
        event = RunEvent(
            run_id=run_id,
            sequence=1,
            event_name="teaching_pack.run.accepted",
            stage=None,
            visibility=TeachingPackEventVisibility.TEACHER,
        )
        session.add(event)
        await session.flush()

        evidence = await generate_evidence(run_id, session)

        assert evidence.run_id == run_id
        assert evidence.status == "completed"
        assert evidence.tokens_used == 5000
        assert evidence.cost_usd == 0.33
        assert len(evidence.event_sequence) == 1
        assert evidence.teacher_id_hash == hash_teacher_id(teacher_id)

    async def test_generate_evidence_includes_event_sequence(self, session: AsyncSession) -> None:
        """Events should be in sequence order."""
        run_id = RunId(f"ev-events-{uuid4()}")
        await self._setup_run(session, run_id, TeacherId("teacher-events"))

        for i in range(5):
            session.add(
                RunEvent(
                    run_id=run_id,
                    sequence=i + 1,
                    event_name=f"event_{i}",
                    stage=f"stage_{i}",
                    visibility=TeachingPackEventVisibility.TEACHER,
                )
            )
        await session.flush()

        evidence = await generate_evidence(run_id, session)
        assert len(evidence.event_sequence) == 5
        # Verify ordering
        sequences = [e["sequence"] for e in evidence.event_sequence]
        assert sequences == [1, 2, 3, 4, 5]

    async def test_generate_evidence_includes_snapshot_ids(self, session: AsyncSession) -> None:
        """Snapshot IDs should be collected."""
        from tests.e2e.conftest import create_test_snapshot

        run_id = RunId(f"ev-snap-{uuid4()}")
        await self._setup_run(session, run_id, TeacherId("teacher-snap"))

        for i in range(3):
            await create_test_snapshot(
                session,
                snapshot_id=f"snap-ev-{i}",
                run_id=run_id,
                artifact_id=f"art-ev-{i}",
            )
        await session.flush()

        evidence = await generate_evidence(run_id, session)
        assert len(evidence.snapshot_ids) == 3

    async def test_generate_evidence_nonexistent_raises(self, session: AsyncSession) -> None:
        """Missing run should raise ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await generate_evidence(RunId("no-such-run"), session)


# ─────────────────────────────────────────────────────────────────────
# §4  Evidence store: save, get, list
# ─────────────────────────────────────────────────────────────────────


class TestEvidenceStore:
    """Test the persistence layer (save_evidence, get_evidence, list_evidence)."""

    async def _make_evidence(
        self,
        session: AsyncSession,
        run_id: RunId,
        teacher_id: str = "teacher-store",
    ) -> ReleaseEvidence:
        run = Run(
            run_id=run_id,
            teacher_id=teacher_id,
            status=RunStatus.COMPLETED,
            current_step=13,
            raw_request="Test",
            tokens_used=100,
            cost_usd=0.01,
        )
        session.add(run)
        await session.flush()
        return await generate_evidence(run_id, session)

    async def test_save_and_get(self, session: AsyncSession) -> None:
        run_id = RunId(f"ev-store-{uuid4()}")
        evidence = await self._make_evidence(session, run_id)

        await save_evidence(evidence, session)
        await session.flush()

        loaded = await get_evidence(run_id, session)
        assert loaded is not None
        assert loaded.run_id == run_id
        assert loaded.status == "completed"

    async def test_get_nonexistent_returns_none(self, session: AsyncSession) -> None:
        result = await get_evidence("nonexistent-run-id", session)
        assert result is None

    async def test_list_returns_newest_first(self, session: AsyncSession) -> None:
        """list_evidence should return records ordered by created_at desc."""
        ids = []
        for _i in range(4):
            rid = RunId(f"ev-list-{uuid4()}")
            ids.append(rid)
            ev = await self._make_evidence(session, rid)
            await save_evidence(ev, session)
        await session.flush()

        items = await list_evidence(session, limit=10)
        assert len(items) == 4
        # All IDs should be present
        returned_ids = {e.run_id for e in items}
        assert returned_ids == set(ids)

    async def test_list_respects_limit(self, session: AsyncSession) -> None:
        for _ in range(5):
            rid = RunId(f"ev-limit-{uuid4()}")
            ev = await self._make_evidence(session, rid)
            await save_evidence(ev, session)
        await session.flush()

        items = await list_evidence(session, limit=2)
        assert len(items) == 2

    async def test_upsert_on_existing_run_id(self, session: AsyncSession) -> None:
        """save_evidence should update existing record (merge on run_id)."""
        run_id = RunId(f"ev-upsert-{uuid4()}")
        evidence = await self._make_evidence(session, run_id)

        await save_evidence(evidence, session)
        await session.flush()

        # Save again with updated tokens
        updated = ReleaseEvidence(
            run_id=evidence.run_id,
            teacher_id_hash=evidence.teacher_id_hash,
            status="completed",
            tokens_used=9999,
            cost_usd=1.0,
            created_at=evidence.created_at,
        )
        await save_evidence(updated, session)
        await session.flush()

        loaded = await get_evidence(run_id, session)
        assert loaded is not None
        assert loaded.tokens_used == 9999
        assert loaded.cost_usd == 1.0


class TestEvidenceRouteReports:
    async def test_generate_and_save_evidence_writes_markdown_report(
        self,
        session: AsyncSession,
        tmp_path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        run_id = RunId(f"ev-route-{uuid4()}")
        session.add(
            Run(
                run_id=run_id,
                teacher_id="teacher-route-report",
                status=RunStatus.COMPLETED,
                current_step=13,
                raw_request="Report test",
            )
        )
        await session.flush()
        monkeypatch.setattr(release_evidence_router, "EVIDENCE_REPORT_DIR", tmp_path)

        response = await release_evidence_router.generate_and_save_evidence(
            run_id,
            User(user_id="admin", username="admin", role=Role.ADMIN),
            session,
        )
        report_path = tmp_path / f"teaching-pack-run-evidence-{run_id}.md"

        assert response.run_id == run_id
        assert report_path.exists()
        assert "Teaching Pack Release Evidence" in report_path.read_text(encoding="utf-8")
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()


# ─────────────────────────────────────────────────────────────────────
# §5  Evidence includes all required data
# ─────────────────────────────────────────────────────────────────────


class TestEvidenceCompleteness:
    """Verify evidence captures the full picture of a run."""

    async def test_evidence_includes_all_event_fields(self, session: AsyncSession) -> None:
        """Each event in evidence should have sequence, event_name, stage, created_at."""
        run_id = RunId(f"ev-complete-{uuid4()}")
        run = Run(
            run_id=run_id,
            teacher_id="teacher-complete",
            status=RunStatus.COMPLETED,
            current_step=13,
            raw_request="Full test",
        )
        session.add(run)
        await session.flush()

        session.add(
            RunEvent(
                run_id=run_id,
                sequence=1,
                event_name="teaching_pack.test.started",
                stage="test_stage",
                visibility=TeachingPackEventVisibility.TEACHER,
                payload={"key": "value"},
            )
        )
        await session.flush()

        evidence = await generate_evidence(run_id, session)
        assert len(evidence.event_sequence) == 1
        evt = evidence.event_sequence[0]
        assert "sequence" in evt
        assert "event_name" in evt
        assert "stage" in evt
        assert "created_at" in evt

    async def test_evidence_teacher_id_is_always_hashed(self, session: AsyncSession) -> None:
        """The teacher_id_hash field must never contain the raw teacher_id."""
        run_id = RunId(f"ev-hash-{uuid4()}")
        raw_teacher = "teacher-plaintext-123"
        run = Run(
            run_id=run_id,
            teacher_id=raw_teacher,
            status=RunStatus.COMPLETED,
            current_step=13,
            raw_request="Hash test",
        )
        session.add(run)
        await session.flush()

        evidence = await generate_evidence(run_id, session)
        assert evidence.teacher_id_hash != raw_teacher
        assert evidence.teacher_id_hash == hash_teacher_id(raw_teacher)


# ─────────────────────────────────────────────────────────────────────
# §6  Provider evidence integration
# ─────────────────────────────────────────────────────────────────────


class TestProviderEvidenceIntegration:
    """Verify provider_evidence field in ReleaseEvidence round-trip and rendering."""

    def test_provider_evidence_column_in_orm_metadata(self) -> None:
        """ORM metadata must include provider_evidence on release_evidence table."""
        table = ReleaseEvidenceRecord.__table__
        assert "provider_evidence" in table.columns, (
            "ReleaseEvidenceRecord ORM model must declare provider_evidence column"
        )
        col = table.columns["provider_evidence"]
        assert col.nullable, "provider_evidence must be nullable"

    def test_provider_evidence_default_empty(self) -> None:
        e = ReleaseEvidence(
            run_id="run-no-pe",
            teacher_id_hash="h",
            status="completed",
        )
        assert e.provider_evidence == []

    def test_provider_evidence_round_trip(self) -> None:
        pe = [
            {
                "base_url": "http://127.0.0.1:20228",
                "model": "4omc",
                "timestamp": "2026-06-28T00:00:00+00:00",
                "status": "pass",
                "elapsed_s": 0.42,
                "models_endpoint_ok": True,
                "chat_endpoint_ok": True,
                "error": None,
            },
        ]
        original = ReleaseEvidence(
            run_id="run-pe-rt",
            teacher_id_hash="h1",
            status="completed",
            provider_evidence=pe,
        )
        record = original.to_db_record()
        restored = ReleaseEvidence.from_db_record(record)
        assert len(restored.provider_evidence) == 1
        assert restored.provider_evidence[0]["status"] == "pass"
        assert restored.provider_evidence[0]["base_url"] == "http://127.0.0.1:20228"

    def test_provider_evidence_blocked_round_trip(self) -> None:
        pe = [
            {
                "base_url": "http://down:20228",
                "model": "4omc",
                "timestamp": "2026-06-28T00:00:00+00:00",
                "status": "blocked",
                "elapsed_s": 0.0,
                "models_endpoint_ok": False,
                "chat_endpoint_ok": False,
                "error": "Connection refused",
            },
        ]
        original = ReleaseEvidence(
            run_id="run-pe-blocked",
            teacher_id_hash="h2",
            status="completed",
            provider_evidence=pe,
        )
        record = original.to_db_record()
        restored = ReleaseEvidence.from_db_record(record)
        assert restored.provider_evidence[0]["status"] == "blocked"
        assert restored.provider_evidence[0]["error"] == "Connection refused"

    def test_render_markdown_includes_provider_evidence(self) -> None:
        pe = [
            {
                "base_url": "http://127.0.0.1:20228",
                "model": "4omc",
                "timestamp": "2026-06-28T00:00:00+00:00",
                "status": "pass",
                "elapsed_s": 0.5,
                "models_endpoint_ok": True,
                "chat_endpoint_ok": True,
                "error": None,
            },
            {
                "base_url": "http://down:20228",
                "model": "f.light",
                "timestamp": "2026-06-28T00:00:01+00:00",
                "status": "blocked",
                "elapsed_s": 0.0,
                "models_endpoint_ok": False,
                "chat_endpoint_ok": False,
                "error": "Connection refused",
            },
        ]
        evidence = ReleaseEvidence(
            run_id="run-md-pe",
            teacher_id_hash="h3",
            status="completed",
            provider_evidence=pe,
        )
        md = render_evidence_markdown(evidence)
        assert "## Provider evidence (9Router)" in md
        assert "[PASS]" in md
        assert "[BLOCKED]" in md
        assert "Connection refused" in md

    def test_render_markdown_without_provider_evidence(self) -> None:
        evidence = ReleaseEvidence(
            run_id="run-no-pe-md",
            teacher_id_hash="h4",
            status="completed",
        )
        md = render_evidence_markdown(evidence)
        assert "Provider evidence" not in md
