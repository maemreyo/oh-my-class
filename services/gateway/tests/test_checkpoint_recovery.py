from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from fastapi import FastAPI
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User
from services.gateway.disaster_recovery import collect_restore_drill_snapshot
from services.gateway.models import Base, Run, RunStatus
from services.gateway.routers.teaching_pack_runs import router
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_models import GateInterrupt, GateInterruptStatus, RunJob, RunJobKind, RunJobStatus, RunStatusHistory

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(lambda sync_connection: Base.metadata.create_all(sync_connection, checkfirst=True))
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(router, prefix="/teaching-packs")

    async def override_session() -> AsyncIterator[AsyncSession]:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as route_session:
            yield route_session
        await engine.dispose()

    app.dependency_overrides[require_teacher] = lambda: User(
        user_id="teacher-drill",
        username="teacher-drill",
        role=Role.TEACHER,
    )
    app.dependency_overrides[get_teaching_pack_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


class TestCheckpointRecovery:
    async def test_interrupted_gate_run_resumes_after_restore_drill(
        self,
        session: AsyncSession,
        client: TestClient,
    ) -> None:
        seed = _RecoverySeed(run_id=f"drill-{uuid4()}", gate_id=f"gate-{uuid4()}")
        await _seed_interrupted_run(session, seed)
        before = await collect_restore_drill_snapshot(session, seed.run_id)

        await _simulate_postgres_restore(session, seed)
        after = await collect_restore_drill_snapshot(session, seed.run_id)
        response = client.post(
            f"/teaching-packs/runs/{seed.run_id}/resume",
            json={
                "gate_id": seed.gate_id,
                "gate_name": "content_approval",
                "action": "approve",
                "response": {"approved": True},
            },
        )

        assert before == after
        assert response.status_code == 202
        body = response.json()
        assert body["run_id"] == seed.run_id
        assert body["job_id"].startswith("job-")
        assert (await collect_restore_drill_snapshot(session, seed.run_id)).active_gate_count == 0

        await session.execute(delete(Run).where(Run.run_id == seed.run_id))
        await session.commit()


class _RecoverySeed:
    def __init__(self, *, run_id: str, gate_id: str) -> None:
        self.run_id = run_id
        self.gate_id = gate_id


async def _seed_interrupted_run(session: AsyncSession, seed: _RecoverySeed) -> None:
    created_at = datetime(2099, 6, 30, 8, tzinfo=UTC)
    session.add(Run(
        run_id=seed.run_id,
        teacher_id="teacher-drill",
        status=RunStatus.AWAITING_APPROVAL,
        raw_request="DR checkpoint restore drill",
        class_info={"grade": 5},
        created_at=created_at,
        updated_at=created_at,
    ))
    session.add(RunStatusHistory(
        run_id=seed.run_id,
        status=RunStatus.AWAITING_APPROVAL,
        stage="teacher_approval",
        reason="restore_drill_gate",
        created_at=created_at,
    ))
    session.add(GateInterrupt(
        gate_id=seed.gate_id,
        run_id=seed.run_id,
        gate_name="content_approval",
        status=GateInterruptStatus.ACTIVE,
        payload={"gate": "content_approval"},
        created_at=created_at,
    ))
    session.add(RunJob(
        job_id=f"job-{uuid4()}",
        run_id=seed.run_id,
        kind=RunJobKind.START,
        status=RunJobStatus.COMPLETED,
        idempotency_key=f"restore-drill:{seed.run_id}:completed",
        payload={"checkpoint_thread_id": seed.run_id},
        created_at=created_at,
        updated_at=created_at,
    ))
    await session.commit()


async def _simulate_postgres_restore(session: AsyncSession, seed: _RecoverySeed) -> None:
    run = (await session.execute(select(Run).where(Run.run_id == seed.run_id))).scalar_one()
    gate = (await session.execute(select(GateInterrupt).where(GateInterrupt.gate_id == seed.gate_id))).scalar_one()
    job = (await session.execute(select(RunJob).where(RunJob.run_id == seed.run_id))).scalar_one()
    history = (await session.execute(select(RunStatusHistory).where(RunStatusHistory.run_id == seed.run_id))).scalar_one()
    restored = {
        "run": _run_restore_payload(run),
        "gate": _gate_restore_payload(gate),
        "job": _job_restore_payload(job),
        "history": _history_restore_payload(history),
    }
    await session.execute(delete(Run).where(Run.run_id == seed.run_id))
    await session.flush()
    session.expunge_all()
    session.add(Run(**restored["run"]))
    session.add(RunStatusHistory(**restored["history"]))
    session.add(GateInterrupt(**restored["gate"]))
    session.add(RunJob(**restored["job"]))
    await session.commit()


def _run_restore_payload(run: Run) -> dict[str, object]:
    return {
        "run_id": run.run_id,
        "teacher_id": run.teacher_id,
        "status": run.status,
        "current_step": run.current_step,
        "raw_request": run.raw_request,
        "class_info": run.class_info,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
    }


def _gate_restore_payload(gate: GateInterrupt) -> dict[str, object]:
    return {
        "gate_id": gate.gate_id,
        "run_id": gate.run_id,
        "gate_name": gate.gate_name,
        "status": gate.status,
        "payload": gate.payload,
        "created_at": gate.created_at,
        "expires_at": gate.expires_at,
    }


def _job_restore_payload(job: RunJob) -> dict[str, object]:
    return {
        "job_id": job.job_id,
        "run_id": job.run_id,
        "kind": job.kind,
        "status": job.status,
        "idempotency_key": job.idempotency_key,
        "payload": job.payload,
        "attempts": job.attempts,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def _history_restore_payload(history: RunStatusHistory) -> dict[str, object]:
    return {
        "run_id": history.run_id,
        "status": history.status,
        "stage": history.stage,
        "reason": history.reason,
        "created_at": history.created_at,
    }
