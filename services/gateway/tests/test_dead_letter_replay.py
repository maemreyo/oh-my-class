"""#124: dead-letter state, claim-pool exclusion, replay, and separation from
ADR-029 quality-escalate.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base, Run
from services.gateway.teaching_pack_control_store import GateInterruptCreate, TeachingPackControlStore
from services.gateway.teaching_pack_job_store import RunJobCreate, TeachingPackJobStore
from services.gateway.teaching_pack_models import GateInterrupt, RunJob, RunJobKind, RunJobStatus
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def session():
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            existing_tables = await connection.run_sync(lambda _connection: set(Base.metadata.tables))
            if "public.run_jobs" not in existing_tables:
                pytest.skip("Teaching Pack run_jobs table is not present")
        async with session_factory() as database_session:
            yield database_session
            await database_session.rollback()
    except (OSError, SQLAlchemyError) as exc:
        pytest.skip(f"Postgres is unavailable for dead-letter tests: {exc}")
    finally:
        await engine.dispose()


async def _create_run(session) -> RunId:
    run_id = RunId(f"test-dlq-{uuid4()}")
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-dlq-test"),
        raw_request="Teach dead-letter replay",
        class_info={"grade": 5},
    ))
    await session.flush()
    return run_id


async def _claim_job(session, run_id: RunId):
    store = TeachingPackJobStore(session)
    await store.enqueue(RunJobCreate(
        job_id=f"job-dlq-{uuid4()}",
        run_id=run_id,
        kind=RunJobKind.START,
        idempotency_key=f"idem-dlq-{uuid4()}",
        payload={"initial_state": {"run_id": run_id}},
    ))
    claimed = await store.claim_next(
        lease_owner="worker-dlq", lease_seconds=30, now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert claimed is not None
    return claimed


async def _cleanup_run(session, run_id: RunId) -> None:
    await session.execute(delete(RunJob).where(RunJob.run_id == run_id))
    await session.execute(delete(GateInterrupt).where(GateInterrupt.run_id == run_id))
    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()


async def test_dead_lettered_job_is_never_reclaimed(session) -> None:
    run_id = await _create_run(session)
    try:
        job = await _claim_job(session, run_id)
        store = TeachingPackJobStore(session)

        marked = await store.mark_dead_letter(
            job.job_id, error_summary="permanent failure", classification="permanent",
        )
        await session.flush()
        assert marked is True

        # claim_next must never pick up a DEAD_LETTER job (mirrors FAILED).
        reclaimed = await store.claim_next(
            lease_owner="worker-other", lease_seconds=30, now=datetime(2026, 1, 1, tzinfo=UTC),
        )
        assert reclaimed is None

        # list_pending must not surface it either.
        pending = await store.list_pending(limit=10)
        assert job.job_id not in {p.job_id for p in pending}
    finally:
        await _cleanup_run(session, run_id)


async def test_dead_letter_records_triage_metadata(session) -> None:
    run_id = await _create_run(session)
    try:
        job = await _claim_job(session, run_id)
        store = TeachingPackJobStore(session)

        await store.mark_dead_letter(
            job.job_id, error_summary="provider returned 500 five times", classification="transient_exhausted",
        )
        await session.flush()

        row = (await session.execute(select(RunJob).where(RunJob.job_id == job.job_id))).scalar_one()
        assert row.status == RunJobStatus.DEAD_LETTER
        assert row.last_error == "provider returned 500 five times"
        assert row.error_classification == "transient_exhausted"
        assert row.dead_lettered_at is not None
        assert row.lease_owner is None
    finally:
        await _cleanup_run(session, run_id)


async def test_replay_resets_a_dead_lettered_job_to_pending_without_duplicating_it(session) -> None:
    run_id = await _create_run(session)
    try:
        job = await _claim_job(session, run_id)
        store = TeachingPackJobStore(session)
        await store.mark_dead_letter(job.job_id, error_summary="boom", classification="permanent")
        await session.flush()

        replayed = await store.replay_dead_letter(job.job_id)
        await session.flush()
        assert replayed is True

        row = (await session.execute(select(RunJob).where(RunJob.job_id == job.job_id))).scalar_one()
        assert row.status == RunJobStatus.PENDING
        assert row.attempts == 0
        assert row.last_error is None
        assert row.error_classification is None
        assert row.dead_lettered_at is None

        # Exactly one row for this idempotency key -- replay reuses the same
        # job row rather than minting a duplicate.
        count = (await session.execute(
            select(RunJob).where(RunJob.run_id == run_id),
        )).scalars().all()
        assert len(count) == 1

        # It's claimable again.
        reclaimed = await store.claim_next(
            lease_owner="worker-replay", lease_seconds=30, now=datetime(2026, 1, 2, tzinfo=UTC),
        )
        assert reclaimed is not None
        assert reclaimed.job_id == job.job_id
    finally:
        await _cleanup_run(session, run_id)


async def test_replay_is_a_no_op_for_a_non_dead_lettered_job(session) -> None:
    run_id = await _create_run(session)
    try:
        job = await _claim_job(session, run_id)  # status is RUNNING, not DEAD_LETTER
        store = TeachingPackJobStore(session)

        replayed = await store.replay_dead_letter(job.job_id)
        await session.flush()

        assert replayed is False
        row = (await session.execute(select(RunJob).where(RunJob.job_id == job.job_id))).scalar_one()
        assert row.status == RunJobStatus.RUNNING
    finally:
        await _cleanup_run(session, run_id)


async def test_dead_lettering_a_job_creates_no_gate_interrupt(session) -> None:
    """#124: infra-poison (dead-letter) must stay structurally separate from
    ADR-029 quality-escalate -- dead-lettering a job never creates a
    GateInterrupt row, which is the mechanism behind the teacher-facing
    quality-escalate/gate path."""
    run_id = await _create_run(session)
    try:
        job = await _claim_job(session, run_id)
        store = TeachingPackJobStore(session)

        await store.mark_dead_letter(job.job_id, error_summary="boom", classification="permanent")
        await session.flush()

        gates = (await session.execute(
            select(GateInterrupt).where(GateInterrupt.run_id == run_id),
        )).scalars().all()
        assert gates == []
    finally:
        await _cleanup_run(session, run_id)


async def test_quality_escalate_gate_interrupt_does_not_touch_run_job_status(session) -> None:
    """The inverse guard: opening a quality-escalate GateInterrupt for a run
    must not change that run's RunJob status to DEAD_LETTER -- the two paths
    never write to each other's state."""
    run_id = await _create_run(session)
    try:
        job = await _claim_job(session, run_id)
        control_store = TeachingPackControlStore(session)

        await control_store.open_gate(GateInterruptCreate(
            gate_id=f"gate-{uuid4()}",
            run_id=run_id,
            gate_name="content_approval",
            payload={"reason": "quality escalation, unrelated to job infra"},
        ))
        await session.flush()

        row = (await session.execute(select(RunJob).where(RunJob.job_id == job.job_id))).scalar_one()
        assert row.status == RunJobStatus.RUNNING
        assert row.error_classification is None
    finally:
        await _cleanup_run(session, run_id)
