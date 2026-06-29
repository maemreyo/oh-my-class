from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import anyio
import pytest
from fastapi import FastAPI
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from services.gateway.auth.dependencies import get_current_user_for_status_stream, require_teacher
from services.gateway.auth.models import Role, User
from services.gateway.models import Base, Run
from services.gateway.routers.teaching_pack_runs import router
from services.gateway.routers.teaching_pack_stream import (
    TeachingPackStreamRequest,
    stream_visible_run_events,
)
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_event_bus import (
    current_run_event_version,
    notify_run_event,
    wait_for_run_event,
)
from services.gateway.teaching_pack_models import (
    GateInterrupt,
    GateResponse,
    RunJob,
    TeachingPackEventVisibility,
)
from services.gateway.teaching_pack_store import (
    TeachingPackEventCreate,
    TeachingPackRunCreate,
    TeachingPackRunStore,
)
from services.gateway.teaching_pack_types import RunId, TeacherId

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
    app.dependency_overrides[get_current_user_for_status_stream] = lambda: User(
        user_id="teacher-route",
        username="teacher-route",
        role=Role.TEACHER,
    )
    app.dependency_overrides[get_teaching_pack_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


class TestTeachingPackStreamRouter:
    def test_status_stream_replays_teacher_events_after_last_event_id(
        self,
        client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_create_run_with_events, run_id)

        response = client.get(
            f"/teaching-packs/run/{run_id}/status?replay_only=true",
            headers={"Last-Event-ID": "1"},
        )

        assert response.status_code == 200
        assert "event: teaching_pack.visible" in response.text
        assert "id: 3" in response.text
        assert "event: teaching_pack.internal" not in response.text
        anyio.run(_delete_run, run_id)

    def test_status_stream_receives_new_visible_event_without_reconnect(
        self,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_create_empty_run, run_id)

        received = anyio.run(_read_live_stream_after_commit, run_id)

        assert "event: teaching_pack.live" in received
        anyio.run(_delete_run, run_id)

    def test_event_bus_wakes_connected_status_waiter(self) -> None:
        run_id = RunId(f"test-{uuid4()}")

        anyio.run(_wait_then_notify, run_id)


async def _skip_if_schema_missing() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(
            lambda sync_connection: set(Base.metadata.tables),
        )
        if "public.run_jobs" not in existing_tables:
            pytest.skip("Teaching Pack route tables are not present")
    await engine.dispose()


async def _create_empty_run(run_id: RunId) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-route"),
            raw_request="Teach streaming",
            class_info={"grade": 5},
        ))
        await session.commit()
    await engine.dispose()


async def _create_run_with_events(run_id: RunId) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        store = TeachingPackRunStore(session)
        await store.create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-route"),
            raw_request="Teach streaming",
            class_info={"grade": 5},
        ))
        await store.write_event(TeachingPackEventCreate(
            run_id=run_id,
            event_name="teaching_pack.hidden",
            visibility=TeachingPackEventVisibility.TEACHER,
            payload={"step": 1},
        ))
        await store.write_event(TeachingPackEventCreate(
            run_id=run_id,
            event_name="teaching_pack.internal",
            visibility=TeachingPackEventVisibility.INTERNAL,
            payload={"step": 2},
        ))
        await store.write_event(TeachingPackEventCreate(
            run_id=run_id,
            event_name="teaching_pack.visible",
            visibility=TeachingPackEventVisibility.TEACHER,
            payload={"step": 3},
        ))
        await session.commit()
    await engine.dispose()


async def _write_live_visible_event(run_id: RunId) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await TeachingPackRunStore(session).write_event(TeachingPackEventCreate(
            run_id=run_id,
            event_name="teaching_pack.live",
            visibility=TeachingPackEventVisibility.TEACHER,
            payload={"step": "live"},
        ))
        await session.commit()
    await engine.dispose()


async def _read_live_stream_after_commit(run_id: RunId) -> str:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        stream = stream_visible_run_events(
            TeachingPackRunStore(session),
            TeachingPackStreamRequest(run_id=run_id, after_sequence=0, replay_only=False),
        )
        async with anyio.create_task_group() as task_group:
            task_group.start_soon(_write_live_visible_event, run_id)
            received = await stream.__anext__()
            task_group.cancel_scope.cancel()
    await engine.dispose()
    return received


async def _wait_then_notify(run_id: RunId) -> None:
    woke_up = False

    async def wait_for_signal() -> None:
        nonlocal woke_up
        woke_up = await wait_for_run_event(run_id, current_run_event_version(run_id), 5.0)

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(wait_for_signal)
        await anyio.lowlevel.checkpoint()
        notify_run_event(run_id)

    assert woke_up is True


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
