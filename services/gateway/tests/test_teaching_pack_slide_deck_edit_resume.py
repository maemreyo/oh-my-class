"""SDE-04: live-path-proof for the gate-resume entry point.

Hits the real `teaching_pack_runs.router` (only `require_teacher`/DB session
overridden, mirroring `test_teaching_pack_contract_resume.py`'s fixture) to
prove `action: "edit"` with a `slide_deck_block_edit` payload is actually
reachable through the `/resume` route and threaded into the enqueued job --
not just exercised via a unit test that calls
`apply_scoped_slide_deck_block_edit_on_artifacts` directly (that direct unit
test also exists, in `packages/agents/tests/test_scoped_repair_loop.py`).
The graph itself (where the business function actually runs) executes in a
background worker this test does not start -- proving the router accepts,
validates, and persists the new payload shape is the "live path" for this
entry point, exactly like the existing contract-confirmation edit tests in
`test_teaching_pack_contract_resume.py` prove only up to job enqueue too.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import anyio
import pytest
from fastapi import FastAPI
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User
from services.gateway.models import Base, Run
from services.gateway.routers.teaching_pack_runs import router
from services.gateway.teaching_pack_control_store import GateInterruptCreate, TeachingPackControlStore
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_models import GateInterrupt, GateResponse, RunJob, RunJobKind
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import JsonObject, RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
def client() -> Iterator[TestClient]:
    anyio.run(_skip_if_schema_missing)
    app = FastAPI()
    app.include_router(router, prefix="/teaching-packs")

    async def override_session() -> AsyncIterator[AsyncSession]:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session
        await engine.dispose()

    app.dependency_overrides[require_teacher] = lambda: User(
        user_id="teacher-route",
        username="teacher-route",
        role=Role.TEACHER,
    )
    app.dependency_overrides[get_teaching_pack_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


def test_content_approval_edit_resume_enqueues_job_with_slide_deck_block_edit(
    client: TestClient,
) -> None:
    run_id = RunId(f"test-{uuid4()}")
    gate_id = f"gate-{uuid4()}"
    anyio.run(_create_run_with_content_approval_gate, run_id, gate_id)

    response = client.post(
        f"/teaching-packs/runs/{run_id}/resume",
        json={
            "gate_id": gate_id,
            "gate_name": "content_approval",
            "action": "edit",
            "response": {
                "edit_type": "scoped_slide_deck_block",
                "slide_deck_block_edit": {
                    "artifact_id": "deck-artifact-1",
                    "block_id": "block-1",
                    "new_content": "Teacher-revised heading.",
                    "rationale": "Clarify the hook.",
                },
            },
        },
    )

    assert response.status_code == 202
    data = response.json()
    kind, job_payload = anyio.run(_get_job_result, run_id, data["job_id"])
    assert kind is RunJobKind.RESUME
    resume_payload = job_payload["resume_payload"]
    assert resume_payload["action"] == "edit"
    assert resume_payload["edit_type"] == "scoped_slide_deck_block"
    assert resume_payload["slide_deck_block_edit"] == {
        "artifact_id": "deck-artifact-1",
        "block_id": "block-1",
        "new_content": "Teacher-revised heading.",
        "rationale": "Clarify the hook.",
    }
    anyio.run(_delete_run, run_id)


async def _skip_if_schema_missing() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(lambda sync_connection: set(Base.metadata.tables))
        if "public.run_jobs" not in existing_tables:
            pytest.skip("Teaching Pack route tables are not present")
    await engine.dispose()


async def _create_run_with_content_approval_gate(run_id: RunId, gate_id: str) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        teacher_id = TeacherId("teacher-route")
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=teacher_id,
            raw_request="Teach a slide deck",
            class_info={"grade": 5},
        ))
        await TeachingPackControlStore(session).open_gate(GateInterruptCreate(
            gate_id=gate_id,
            run_id=run_id,
            gate_name="content_approval",
            payload={},
        ))
        await session.commit()
    await engine.dispose()


async def _get_job_result(run_id: RunId, job_id: str) -> tuple[RunJobKind, JsonObject]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(select(RunJob.kind, RunJob.payload).where(
            RunJob.run_id == run_id,
            RunJob.job_id == job_id,
        ))
        row = result.one()
    await engine.dispose()
    return row[0], row[1]


async def _delete_run(run_id: RunId) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(delete(GateResponse).where(GateResponse.run_id == run_id))
        await session.execute(delete(GateInterrupt).where(GateInterrupt.run_id == run_id))
        await session.execute(delete(RunJob).where(RunJob.run_id == run_id))
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()
    await engine.dispose()
