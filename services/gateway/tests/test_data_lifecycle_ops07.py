"""Integration tests for OPS-07's generalized per-data-class purge + KPI
rollup, against real PostgreSQL (same pattern as test_soft_delete_retention.py).

Requires a running PostgreSQL instance (DATABASE_URL).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import anyio
import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Artifact, Run, RunStatus
from services.gateway.purge import (
    purge_expired_artifacts,
    purge_expired_run_events,
    purge_expired_runs,
    purge_expired_snapshots,
)
from services.gateway.run_event_rollup import (
    RunEventKpiRollup,
    days_needing_rollup_before_purge,
    ensure_kpi_rollup_for_day,
)
from services.gateway.teaching_pack_artifact_models import (
    ArtifactCheckStatus,
    ArtifactWorkflow,
    ArtifactWorkflowStatus,
)
from services.gateway.teaching_pack_models import RunEvent, TeachingPackEventVisibility
from services.gateway.teaching_pack_snapshot_models import ArtifactSnapshot
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


async def _skip_if_schema_missing() -> None:
    try:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        async with engine.connect():
            pass
        await engine.dispose()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"PostgreSQL not available: {exc}")


def _session_factory():
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def _create_terminal_deleted_run(run_id: RunId, deleted_days_ago: int) -> None:
    engine, session_factory = _session_factory()
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-test"),
            raw_request="OPS-07 test run",
            class_info={"grade": 5},
        ))
        await session.flush()
        run = (await session.execute(select(Run).where(Run.run_id == run_id))).scalar_one()
        run.status = RunStatus.COMPLETED
        run.deleted_at = datetime.now(UTC) - timedelta(days=deleted_days_ago)
        run.deleted_by = "test"
        await session.commit()
    await engine.dispose()


async def _add_event(
    run_id: RunId, created_at: datetime, event_name: str = "teaching_pack.run.completed",
) -> None:
    engine, session_factory = _session_factory()
    async with session_factory() as session:
        session.add(RunEvent(
            run_id=run_id,
            sequence=1,
            event_name=event_name,
            visibility=TeachingPackEventVisibility.TEACHER,
            payload={},
            created_at=created_at,
        ))
        await session.commit()
    await engine.dispose()


async def _add_snapshot(run_id: RunId) -> str:
    snapshot_id = f"snap-{uuid4()}"
    engine, session_factory = _session_factory()
    async with session_factory() as session:
        session.add(ArtifactSnapshot(
            snapshot_id=snapshot_id,
            run_id=run_id,
            artifact_id="artifact-1",
            artifact_type="worksheet",
            content_hash=f"hash-{uuid4()}",
            html_hash=f"html-{uuid4()}",
            rendered_html="<p>test</p>",
            student_rendered_html="<p>test</p>",
            renderer_version="v1",
        ))
        await session.commit()
    await engine.dispose()
    return snapshot_id


async def _add_artifact_and_workflow(run_id: RunId) -> str:
    artifact_id = f"art-{uuid4()}"
    engine, session_factory = _session_factory()
    async with session_factory() as session:
        session.add(Artifact(
            artifact_id=artifact_id,
            run_id=run_id,
            artifact_type="worksheet",
            title="Test artifact",
        ))
        session.add(ArtifactWorkflow(
            workflow_id=f"wf-{uuid4()}",
            run_id=run_id,
            artifact_id=artifact_id,
            artifact_type="worksheet",
            status=ArtifactWorkflowStatus.PASSED,
            research_guidance_id="rg-1",
            validation_status=ArtifactCheckStatus.PASSED,
            judge_status=ArtifactCheckStatus.PASSED,
        ))
        await session.commit()
    await engine.dispose()
    return artifact_id


async def _cleanup(run_id: RunId) -> None:
    engine, session_factory = _session_factory()
    async with session_factory() as session:
        await session.execute(delete(RunEvent).where(RunEvent.run_id == run_id))
        await session.execute(delete(ArtifactSnapshot).where(ArtifactSnapshot.run_id == run_id))
        await session.execute(delete(Artifact).where(Artifact.run_id == run_id))
        await session.execute(delete(ArtifactWorkflow).where(ArtifactWorkflow.run_id == run_id))
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()
    await engine.dispose()


async def _run(coro_factory):
    engine, session_factory = _session_factory()
    async with session_factory() as session:
        result = await coro_factory(session)
        await session.commit()
    await engine.dispose()
    return result


async def _delete_rollup(day: date) -> None:
    engine, session_factory = _session_factory()
    async with session_factory() as session:
        await session.execute(delete(RunEventKpiRollup).where(RunEventKpiRollup.day == day))
        await session.commit()
    await engine.dispose()


@pytest.fixture(autouse=True)
def _require_postgres() -> None:
    anyio.run(_skip_if_schema_missing)


class TestGeneralizedPurgeByDataClass:
    def test_events_purged_independently_of_snapshots_and_run(self) -> None:
        """Events (90d default) clear their own retention before the run row
        (365d default) does -- purge_expired_run_events should delete the
        RunEvent rows without touching the Run or its snapshots."""
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_create_terminal_deleted_run, run_id, 100)
        anyio.run(_add_event, run_id, datetime.now(UTC) - timedelta(days=100))
        anyio.run(_add_snapshot, run_id)

        deleted = anyio.run(_run, lambda session: purge_expired_run_events(session))
        assert deleted >= 1

        remaining_events = anyio.run(_run, lambda session: session.execute(
            select(RunEvent).where(RunEvent.run_id == run_id),
        ))
        assert list(remaining_events.scalars()) == []

        run = anyio.run(_run, lambda session: session.execute(
            select(Run).where(Run.run_id == run_id),
        ))
        # run row untouched at 100d (< 365d run_metadata retention)
        assert run.scalar_one_or_none() is not None
        anyio.run(_cleanup, run_id)

    def test_events_not_purged_before_events_retention_elapses(self) -> None:
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_create_terminal_deleted_run, run_id, 10)
        anyio.run(_add_event, run_id, datetime.now(UTC) - timedelta(days=10))

        deleted = anyio.run(_run, lambda session: purge_expired_run_events(session))
        assert deleted == 0
        anyio.run(_cleanup, run_id)

    def test_snapshots_purged_at_snapshots_retention(self) -> None:
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_create_terminal_deleted_run, run_id, 200)
        anyio.run(_add_snapshot, run_id)

        deleted = anyio.run(_run, lambda session: purge_expired_snapshots(session))
        assert deleted >= 1
        anyio.run(_cleanup, run_id)

    def test_artifacts_have_no_fk_cascade_and_are_purged_explicitly(self) -> None:
        """Artifact.run_id/ArtifactWorkflow.run_id are plain strings, not FKs
        -- purge_expired_artifacts must delete them explicitly or they'd be
        orphaned forever once the run row is gone."""
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_create_terminal_deleted_run, run_id, 200)
        anyio.run(_add_artifact_and_workflow, run_id)

        deleted = anyio.run(_run, lambda session: purge_expired_artifacts(session))
        assert deleted >= 1

        remaining = anyio.run(_run, lambda session: session.execute(
            select(Artifact).where(Artifact.run_id == run_id),
        ))
        assert list(remaining.scalars()) == []
        anyio.run(_cleanup, run_id)

    def test_run_events_pending_run_never_purged_regardless_of_age(self) -> None:
        """Same ADR-034 §5 safety property, exercised on the events-specific
        purge path (not just the whole-run path)."""
        engine, session_factory = _session_factory()

        async def _create_pending() -> None:
            async with session_factory() as session:
                await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
                    run_id=run_id,
                    teacher_id=TeacherId("teacher-test"),
                    raw_request="pending run",
                    class_info={"grade": 5},
                ))
                await session.flush()
                run = (await session.execute(select(Run).where(Run.run_id == run_id))).scalar_one()
                run.deleted_at = datetime.now(UTC) - timedelta(days=1000)
                await session.commit()

        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_create_pending)
        anyio.run(_add_event, run_id, datetime.now(UTC) - timedelta(days=1000))

        deleted = anyio.run(_run, lambda session: purge_expired_run_events(session))
        assert deleted == 0  # run.status is still PENDING -- never eligible
        anyio.run(_cleanup, run_id)
        anyio.run(engine.dispose)


class TestKpiRollupBeforePrune:
    def test_rollup_captures_success_and_fail_counts_before_events_are_deleted(self) -> None:
        run_id = RunId(f"test-{uuid4()}")
        day = date(2026, 1, 15)
        created_at = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)
        anyio.run(_create_terminal_deleted_run, run_id, 100)
        anyio.run(_add_event, run_id, created_at, "teaching_pack.run.completed")

        rollup = anyio.run(_run, lambda session: ensure_kpi_rollup_for_day(session, day))
        assert rollup.success_count >= 1
        assert rollup.day == day

        # Now the events can be purged -- the rollup already survives them.
        anyio.run(_run, lambda session: purge_expired_run_events(session))
        remaining = anyio.run(_run, lambda session: session.execute(
            select(RunEventKpiRollup).where(RunEventKpiRollup.day == day),
        ))
        assert remaining.scalar_one().success_count >= 1
        anyio.run(_cleanup, run_id)
        anyio.run(_delete_rollup, day)

    def test_ensure_rollup_is_idempotent(self) -> None:
        day = date(2026, 1, 16)
        first = anyio.run(_run, lambda session: ensure_kpi_rollup_for_day(session, day))
        second = anyio.run(_run, lambda session: ensure_kpi_rollup_for_day(session, day))
        assert first.day == second.day
        anyio.run(_delete_rollup, day)

    def test_days_needing_rollup_before_purge_finds_old_event_days(self) -> None:
        run_id = RunId(f"test-{uuid4()}")
        old_day_dt = datetime.now(UTC) - timedelta(days=95)
        anyio.run(_create_terminal_deleted_run, run_id, 95)
        anyio.run(_add_event, run_id, old_day_dt)

        def _query(session: object) -> object:
            return days_needing_rollup_before_purge(session, events_retention_days=90)

        days = anyio.run(_run, _query)
        assert old_day_dt.date() in days
        anyio.run(_cleanup, run_id)


class TestPurgeExpiredRunsStillWorksEndToEnd:
    def test_full_run_purge_removes_cascaded_artifacts_too(self) -> None:
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_create_terminal_deleted_run, run_id, 400)
        anyio.run(_add_artifact_and_workflow, run_id)
        anyio.run(_add_snapshot, run_id)
        anyio.run(_add_event, run_id, datetime.now(UTC) - timedelta(days=400))

        purged = anyio.run(_run, lambda session: purge_expired_runs(session))
        assert run_id in purged

        remaining_artifacts = anyio.run(_run, lambda session: session.execute(
            select(Artifact).where(Artifact.run_id == run_id),
        ))
        assert list(remaining_artifacts.scalars()) == []


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
