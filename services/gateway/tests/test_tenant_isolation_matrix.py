from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

import anyio
import pytest
from fastapi import FastAPI
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from services.gateway.auth.dependencies import (
    get_current_user,
    get_current_user_for_status_stream,
    require_teacher,
)
from services.gateway.auth.models import Role, User
from services.gateway.middleware.error_handler import register_exception_handlers
from services.gateway.models import Base, Run, RunStatus
from services.gateway.notification_models import NotificationEvent
from services.gateway.notification_store import create_notification, deliver_notification
from services.gateway.routers.notifications import router as notifications_router
from services.gateway.routers.teaching_pack_previews import router as previews_router
from services.gateway.routers.teaching_pack_runs import router as runs_router
from services.gateway.teaching_pack_control_store import GateInterruptCreate, TeachingPackControlStore
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_models import GateInterrupt, GateResponse, RunEvent, RunJob
from services.gateway.teaching_pack_snapshot_models import ArtifactSnapshot
from services.gateway.teaching_pack_snapshot_store import (
    ArtifactSnapshotCreate,
    TeachingPackSnapshotStore,
)
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"
OWNER_TEACHER = "tenant-owner"
OTHER_TEACHER = "tenant-other"


@dataclass(frozen=True, slots=True)
class EndpointCase:
    method: Literal["GET", "POST", "DELETE"]
    path: str
    body: dict[str, str] | dict[str, list[str]] | None = None


@pytest.fixture
def other_teacher_client() -> Iterator[TestClient]:
    anyio.run(_skip_if_schema_missing)
    app = _build_app(OTHER_TEACHER)
    with TestClient(app) as test_client:
        yield test_client


class TestTenantIsolationMatrix:
    @pytest.mark.parametrize("case", [
        EndpointCase("GET", "/teaching-packs/run/{run_id}"),
        EndpointCase("GET", "/teaching-packs/run/{run_id}/status?replay_only=true"),
        EndpointCase("POST", "/teaching-packs/run/{run_id}/cancel"),
        EndpointCase("DELETE", "/teaching-packs/run/{run_id}"),
        EndpointCase(
            "POST",
            "/teaching-packs/run/{run_id}/resume",
            {"gate_id": "{gate_id}", "gate_name": "blueprint_approval", "action": "approve"},
        ),
        EndpointCase("GET", "/teaching-packs/run/{run_id}/snapshots/{snapshot_id}"),
        EndpointCase("GET", "/teaching-packs/run/{run_id}/snapshots/{snapshot_id}/preview"),
        EndpointCase(
            "POST",
            "/teaching-packs/run/{run_id}/approved-snapshots",
            {"snapshot_ids": ["{snapshot_id}"]},
        ),
    ])
    def test_other_teacher_cannot_access_owner_run_endpoints(
        self,
        other_teacher_client: TestClient,
        case: EndpointCase,
    ) -> None:
        run_id = RunId(f"tenant-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_owner_run, run_id, gate_id, snapshot_id)

        response = _request_case(other_teacher_client, case, run_id, gate_id, snapshot_id)

        assert response.status_code in (403, 404)
        anyio.run(_delete_run, run_id)

    def test_other_teacher_cannot_see_owner_notification(self, other_teacher_client: TestClient) -> None:
        run_id = RunId(f"tenant-{uuid4()}")
        notification_id = f"notif-{uuid4()}"
        anyio.run(_create_owner_run, run_id, f"gate-{uuid4()}", f"snap-{uuid4()}")
        anyio.run(_create_notification, run_id, notification_id)

        list_response = other_teacher_client.get("/notifications")
        read_response = other_teacher_client.post(f"/notifications/{notification_id}/read")
        dismiss_response = other_teacher_client.post(
            f"/notifications/{notification_id}/dismiss",
            json={"channel": "in_app"},
        )

        assert list_response.status_code == 200
        assert list_response.json() == []
        assert read_response.status_code == 404
        assert dismiss_response.status_code == 404
        anyio.run(_delete_run, run_id)


def _build_app(user_id: str) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(runs_router, prefix="/teaching-packs")
    app.include_router(previews_router, prefix="/teaching-packs")
    app.include_router(notifications_router, prefix="/notifications")
    user = User(user_id=user_id, username=user_id, role=Role.TEACHER)
    app.dependency_overrides[require_teacher] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_user_for_status_stream] = lambda: user
    app.dependency_overrides[get_teaching_pack_session] = _session
    return app


async def _session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


async def _skip_if_schema_missing() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(lambda _: set(Base.metadata.tables))
        required_tables = {
            "public.artifact_snapshots",
            "public.gate_interrupts",
            "public.notifications",
        }
        if not required_tables.issubset(existing_tables):
            pytest.skip("Tenant isolation tables are not present")
    await engine.dispose()


async def _create_owner_run(run_id: RunId, gate_id: str, snapshot_id: str) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId(OWNER_TEACHER),
            raw_request="Tenant isolation test",
            class_info={"grade": 5},
        ))
        run = await session.get(Run, run_id)
        if run is not None:
            run.status = RunStatus.AWAITING_APPROVAL
        await TeachingPackControlStore(session).open_gate(GateInterruptCreate(
            gate_id=gate_id,
            run_id=run_id,
            gate_name="blueprint_approval",
            payload={"topic": "Fractions"},
        ))
        await TeachingPackSnapshotStore(session).create_snapshot(ArtifactSnapshotCreate(
            snapshot_id=snapshot_id,
            run_id=run_id,
            artifact_id="lesson-1",
            artifact_type="lesson",
            content_json={"title": f"Fractions {run_id}", "sections": []},
            rendered_html=f"<!DOCTYPE html><html><body>oh-my-class {run_id}</body></html>",
            renderer_version="renderer@test",
            template_version="template@test",
            theme_version="theme@test",
        ))
        await session.commit()
    await engine.dispose()


async def _create_notification(run_id: RunId, notification_id: str) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        created_id = await create_notification(
            NotificationEvent(
                event_id=notification_id,
                run_id=run_id,
                teacher_id=OWNER_TEACHER,
                event_type="content_preview_ready",
                title="Preview ready",
                message="Review your pack",
            ),
            session,
        )
        await deliver_notification(created_id, "in_app", session)
        await session.commit()
    await engine.dispose()


def _request_case(
    client: TestClient,
    case: EndpointCase,
    run_id: RunId,
    gate_id: str,
    snapshot_id: str,
):
    path = case.path.format(run_id=run_id, gate_id=gate_id, snapshot_id=snapshot_id)
    match case.method:
        case "GET":
            return client.get(path)
        case "POST":
            body = _format_body(case.body, gate_id, snapshot_id)
            return client.post(path, json=body)
        case "DELETE":
            return client.delete(path)


def _format_body(
    body: dict[str, str] | dict[str, list[str]] | None,
    gate_id: str,
    snapshot_id: str,
) -> dict[str, str] | dict[str, list[str]] | None:
    match body:
        case None:
            return None
        case {"snapshot_ids": snapshot_ids}:
            if not isinstance(snapshot_ids, list):
                return None
            return {"snapshot_ids": [item.format(snapshot_id=snapshot_id) for item in snapshot_ids]}
        case {"gate_id": gate_template, "gate_name": gate_name, "action": action}:
            if not isinstance(gate_template, str):
                return None
            return {
                "gate_id": gate_template.format(gate_id=gate_id),
                "gate_name": str(gate_name),
                "action": str(action),
            }


async def _delete_run(run_id: RunId) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(delete(ArtifactSnapshot).where(ArtifactSnapshot.run_id == run_id))
        await session.execute(delete(GateResponse).where(GateResponse.run_id == run_id))
        await session.execute(delete(GateInterrupt).where(GateInterrupt.run_id == run_id))
        await session.execute(delete(RunJob).where(RunJob.run_id == run_id))
        await session.execute(delete(RunEvent).where(RunEvent.run_id == run_id))
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()
    await engine.dispose()
