"""OPS-07: the scheduled cleanup orchestrator's dry-run/commit boundary,
against real PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import anyio
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.data_lifecycle_cleanup import run_data_lifecycle_cleanup
from services.gateway.models import Run, RunStatus
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


async def _skip_if_unavailable() -> None:
    try:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        async with engine.connect():
            pass
        await engine.dispose()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"PostgreSQL not available: {exc}")


@pytest.fixture(autouse=True)
def _require_postgres() -> None:
    anyio.run(_skip_if_unavailable)


def _engine_and_factory():
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def _make_prunable_run(run_id: RunId) -> None:
    engine, session_factory = _engine_and_factory()
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-test"),
            raw_request="cleanup test",
            class_info={"grade": 5},
        ))
        await session.flush()
        run = (await session.execute(select(Run).where(Run.run_id == run_id))).scalar_one()
        run.status = RunStatus.COMPLETED
        run.deleted_at = datetime.now(UTC) - timedelta(days=400)
        run.deleted_by = "test"
        await session.commit()
    await engine.dispose()


async def _get_run(run_id: RunId) -> Run | None:
    engine, session_factory = _engine_and_factory()
    async with session_factory() as session:
        run = (await session.execute(select(Run).where(Run.run_id == run_id))).scalar_one_or_none()
        if run is not None:
            session.expunge(run)
    await engine.dispose()
    return run


async def _cleanup(run_id: RunId) -> None:
    engine, session_factory = _engine_and_factory()
    async with session_factory() as session:
        await session.execute(Run.__table__.delete().where(Run.run_id == run_id))
        await session.commit()
    await engine.dispose()


def test_dry_run_reports_would_be_purge_but_leaves_data_intact() -> None:
    run_id = RunId(f"test-{uuid4()}")
    anyio.run(_make_prunable_run, run_id)

    async def _run() -> object:
        engine, session_factory = _engine_and_factory()
        async with session_factory() as session:
            result = await run_data_lifecycle_cleanup(session, dry_run=True)
        await engine.dispose()
        return result

    result = anyio.run(_run)
    assert run_id in result.purged_runs
    assert result.dry_run is True

    # Dry run must not have actually committed the deletion.
    run = anyio.run(_get_run, run_id)
    assert run is not None
    anyio.run(_cleanup, run_id)


def test_real_run_actually_purges() -> None:
    run_id = RunId(f"test-{uuid4()}")
    anyio.run(_make_prunable_run, run_id)

    async def _run() -> object:
        engine, session_factory = _engine_and_factory()
        async with session_factory() as session:
            result = await run_data_lifecycle_cleanup(session, dry_run=False)
        await engine.dispose()
        return result

    result = anyio.run(_run)
    assert run_id in result.purged_runs
    assert result.dry_run is False

    run = anyio.run(_get_run, run_id)
    assert run is None


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
