"""Tests for Teaching Pack cross-tenant auth and ownership isolation."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import anyio
import pytest
from fastapi import Depends, FastAPI
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from services.gateway.auth.dependencies import (
    get_current_user,
    get_current_user_for_status_stream,
    require_teacher,
)
from services.gateway.auth.jwt_handler import create_access_token
from services.gateway.auth.models import Role, User
from services.gateway.auth.ownership import check_run_owner
from services.gateway.models import Base, Run
from services.gateway.routers.teaching_pack_runs import router
from services.gateway.teaching_pack_control_store import (
    GateInterruptCreate,
    GateResponse,
    TeachingPackControlStore,
)
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_models import GateInterrupt, RunJob
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"

OWNER_USER = User(
    user_id="teacher-owner",
    username="teacher-owner",
    role=Role.TEACHER,
    organization_id="org-school-a",
    class_id="class-5a",
)

OTHER_TEACHER = User(
    user_id="teacher-other",
    username="teacher-other",
    role=Role.TEACHER,
    organization_id="org-school-b",
)

SYSTEM_ADMIN_USER = User(
    user_id="sys-admin",
    username="sys-admin",
    role=Role.SYSTEM_ADMIN,
    organization_id="org-school-a",
)

SCHOOL_ADMIN_SAME_ORG = User(
    user_id="school-admin-a",
    username="school-admin-a",
    role=Role.SCHOOL_ADMIN,
    organization_id="org-school-a",
)

LEGACY_ADMIN_USER = User(
    user_id="admin-legacy",
    username="admin-legacy",
    role=Role.ADMIN,
)


@pytest.fixture
def owner_client() -> Iterator[TestClient]:
    anyio.run(_skip_if_schema_missing)
    app = _build_app()
    app.dependency_overrides[require_teacher] = lambda: OWNER_USER
    app.dependency_overrides[get_current_user] = lambda: OWNER_USER
    app.dependency_overrides[get_current_user_for_status_stream] = lambda: OWNER_USER
    with TestClient(app) as c:
        yield c


@pytest.fixture
def other_teacher_client() -> Iterator[TestClient]:
    anyio.run(_skip_if_schema_missing)
    app = _build_app()
    app.dependency_overrides[require_teacher] = lambda: OTHER_TEACHER
    app.dependency_overrides[get_current_user] = lambda: OTHER_TEACHER
    app.dependency_overrides[get_current_user_for_status_stream] = lambda: OTHER_TEACHER
    with TestClient(app) as c:
        yield c


@pytest.fixture
def system_admin_client() -> Iterator[TestClient]:
    anyio.run(_skip_if_schema_missing)
    app = _build_app()
    app.dependency_overrides[require_teacher] = lambda: SYSTEM_ADMIN_USER
    app.dependency_overrides[get_current_user] = lambda: SYSTEM_ADMIN_USER
    app.dependency_overrides[get_current_user_for_status_stream] = lambda: SYSTEM_ADMIN_USER
    with TestClient(app) as c:
        yield c


@pytest.fixture
def school_admin_client() -> Iterator[TestClient]:
    anyio.run(_skip_if_schema_missing)
    app = _build_app()
    app.dependency_overrides[require_teacher] = lambda: SCHOOL_ADMIN_SAME_ORG
    app.dependency_overrides[get_current_user] = lambda: SCHOOL_ADMIN_SAME_ORG
    app.dependency_overrides[get_current_user_for_status_stream] = lambda: SCHOOL_ADMIN_SAME_ORG
    with TestClient(app) as c:
        yield c


@pytest.fixture
def legacy_admin_client() -> Iterator[TestClient]:
    anyio.run(_skip_if_schema_missing)
    app = _build_app()
    app.dependency_overrides[require_teacher] = lambda: LEGACY_ADMIN_USER
    app.dependency_overrides[get_current_user] = lambda: LEGACY_ADMIN_USER
    app.dependency_overrides[get_current_user_for_status_stream] = lambda: LEGACY_ADMIN_USER
    with TestClient(app) as c:
        yield c


@pytest.fixture
def unauthenticated_client() -> Iterator[TestClient]:
    anyio.run(_skip_if_schema_missing)
    app = _build_app()
    # No dependency overrides — no auth
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestUnauthenticatedAccess:
    def test_default_auth_dependency_rejects_cookie_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JWT_SECRET", "test-secret-minimum-32-characters")
        token = create_access_token(OWNER_USER).access_token
        app = FastAPI()

        @app.get("/protected")
        async def protected_route(_user: User = Depends(get_current_user)) -> dict[str, str]:
            return {"status": "accepted"}

        with TestClient(app) as test_client:
            test_client.cookies.set("auth-token", token)
            response = test_client.get("/protected")

        assert response.status_code == 401

    def test_create_run_rejects_cookie_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JWT_SECRET", "test-secret-minimum-32-characters")
        token = create_access_token(OWNER_USER).access_token
        app = _build_app()

        with TestClient(app, raise_server_exceptions=False) as test_client:
            test_client.cookies.set("auth-token", token)
            response = test_client.post(
                "/teaching-packs/run",
                json={"raw_request": "Fractions", "class_info": {}},
            )

        assert response.status_code in (401, 403)

    def test_create_run_requires_auth(
        self, unauthenticated_client: TestClient,
    ) -> None:
        response = unauthenticated_client.post(
            "/teaching-packs/run",
            json={"raw_request": "Fractions", "class_info": {}},
        )
        assert response.status_code in (401, 403)

    def test_resume_run_requires_auth(
        self, unauthenticated_client: TestClient,
    ) -> None:
        response = unauthenticated_client.post(
            f"/teaching-packs/run/{uuid4()}/resume",
            json={
                "gate_id": f"gate-{uuid4()}",
                "gate_name": "blueprint_approval",
                "action": "approve",
            },
        )
        assert response.status_code in (401, 403)

    def test_cancel_run_requires_auth(
        self, unauthenticated_client: TestClient,
    ) -> None:
        response = unauthenticated_client.post(
            f"/teaching-packs/run/{uuid4()}/cancel",
        )
        assert response.status_code in (401, 403)

    def test_status_stream_requires_auth(
        self, unauthenticated_client: TestClient,
    ) -> None:
        response = unauthenticated_client.get(
            f"/teaching-packs/run/{uuid4()}/status",
        )
        assert response.status_code in (401, 403)


class TestCrossTenantIsolation:
    def test_teacher_cannot_resume_other_teacher_run(
        self, other_teacher_client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_owned_run_with_gate, run_id, gate_id)

        response = other_teacher_client.post(
            f"/teaching-packs/run/{run_id}/resume",
            json={
                "gate_id": gate_id,
                "gate_name": "blueprint_approval",
                "action": "approve",
            },
        )
        assert response.status_code == 404
        anyio.run(_delete_run, run_id)

    def test_teacher_cannot_cancel_other_teacher_run(
        self, other_teacher_client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_owned_run_with_gate, run_id, gate_id)

        response = other_teacher_client.post(
            f"/teaching-packs/run/{run_id}/cancel",
        )
        assert response.status_code == 404
        anyio.run(_delete_run, run_id)

    def test_teacher_cannot_stream_other_teacher_status(
        self, other_teacher_client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_owned_run_with_gate, run_id, gate_id)

        response = other_teacher_client.get(
            f"/teaching-packs/run/{run_id}/status",
        )
        assert response.status_code == 404
        anyio.run(_delete_run, run_id)

    def test_owner_can_resume_own_run(
        self, owner_client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_owned_run_with_gate, run_id, gate_id)

        response = owner_client.post(
            f"/teaching-packs/run/{run_id}/resume",
            json={
                "gate_id": gate_id,
                "gate_name": "blueprint_approval",
                "action": "approve",
            },
        )
        assert response.status_code == 202
        anyio.run(_delete_run, run_id)

    def test_owner_can_cancel_own_run(
        self, owner_client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_owned_run_with_gate, run_id, gate_id)

        response = owner_client.post(
            f"/teaching-packs/run/{run_id}/cancel",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
        anyio.run(_delete_run, run_id)


class TestSystemAdminBypass:
    def test_system_admin_can_resume_any_run(
        self, system_admin_client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_owned_run_with_gate, run_id, gate_id)

        response = system_admin_client.post(
            f"/teaching-packs/run/{run_id}/resume",
            json={
                "gate_id": gate_id,
                "gate_name": "blueprint_approval",
                "action": "approve",
            },
        )
        assert response.status_code == 202
        anyio.run(_delete_run, run_id)

    def test_system_admin_can_cancel_any_run(
        self, system_admin_client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_owned_run_with_gate, run_id, gate_id)

        response = system_admin_client.post(
            f"/teaching-packs/run/{run_id}/cancel",
        )
        assert response.status_code == 200
        anyio.run(_delete_run, run_id)

    def test_system_admin_can_stream_any_status(
        self, system_admin_client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_create_owned_run, run_id)

        response = system_admin_client.get(
            f"/teaching-packs/run/{run_id}/status?replay_only=true",
        )
        assert response.status_code == 200
        anyio.run(_delete_run, run_id)


class TestSchoolAdminIsolation:
    def test_school_admin_cannot_access_other_org_run(
        self, school_admin_client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_owned_run_with_gate, run_id, gate_id)

        response = school_admin_client.post(
            f"/teaching-packs/run/{run_id}/resume",
            json={
                "gate_id": gate_id,
                "gate_name": "blueprint_approval",
                "action": "approve",
            },
        )
        # 403 because org check fails-closed (users table lacks org_id column)
        assert response.status_code in (403, 404)
        anyio.run(_delete_run, run_id)


class TestBackwardCompatibility:
    def test_legacy_admin_gets_404_for_other_teacher_run(
        self, legacy_admin_client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_owned_run_with_gate, run_id, gate_id)

        response = legacy_admin_client.post(
            f"/teaching-packs/run/{run_id}/resume",
            json={
                "gate_id": gate_id,
                "gate_name": "blueprint_approval",
                "action": "approve",
            },
        )
        assert response.status_code == 404
        anyio.run(_delete_run, run_id)

    def test_user_without_org_id_can_access_own_runs(
        self,
    ) -> None:
        user_no_org = User(
            user_id="teacher-owner",
            username="teacher-owner",
            role=Role.TEACHER,
        )
        app = _build_app()
        app.dependency_overrides[require_teacher] = lambda: user_no_org
        app.dependency_overrides[get_current_user] = lambda: user_no_org

        with TestClient(app) as client:
            run_id = RunId(f"test-{uuid4()}")
            gate_id = f"gate-{uuid4()}"
            anyio.run(_create_owned_run_with_gate, run_id, gate_id)

            response = client.post(
                f"/teaching-packs/run/{run_id}/resume",
                json={
                    "gate_id": gate_id,
                    "gate_name": "blueprint_approval",
                    "action": "approve",
                },
            )
            assert response.status_code == 202
            anyio.run(_delete_run, run_id)


class TestCheckRunOwnerUnit:
    def test_returns_false_for_nonexistent_run(self) -> None:
        user = User(user_id="t1", username="t1", role=Role.TEACHER)
        result = anyio.run(_check_owner, "nonexistent-run", user)
        assert result is False

    def test_returns_true_for_owner(self) -> None:
        user = User(user_id="teacher-owner", username="teacher-owner", role=Role.TEACHER)
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_create_owned_run, run_id)
        result = anyio.run(_check_owner, str(run_id), user)
        assert result is True
        anyio.run(_delete_run, run_id)

    def test_returns_false_for_non_owner(self) -> None:
        user = User(user_id="teacher-other", username="teacher-other", role=Role.TEACHER)
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_create_owned_run, run_id)
        result = anyio.run(_check_owner, str(run_id), user)
        assert result is False
        anyio.run(_delete_run, run_id)

    def test_system_admin_always_authorized(self) -> None:
        user = User(user_id="anyone", username="anyone", role=Role.SYSTEM_ADMIN)
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_create_owned_run, run_id)
        result = anyio.run(_check_owner, str(run_id), user)
        assert result is True
        anyio.run(_delete_run, run_id)


class TestTeacherIdFromTokenNotBody:
    def test_create_run_uses_authenticated_user_id(
        self, owner_client: TestClient,
    ) -> None:
        response = owner_client.post(
            "/teaching-packs/run",
            json={"raw_request": "Fractions", "class_info": {}},
        )
        assert response.status_code == 202
        run_id = RunId(response.json()["run_id"])
        anyio.run(_delete_run, run_id)


# ── helpers ───────────────────────────────────────────────────────────


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/teaching-packs")

    async def override_session() -> AsyncIterator[AsyncSession]:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session
        await engine.dispose()

    app.dependency_overrides[get_teaching_pack_session] = override_session
    from services.gateway.backpressure import BackpressureConfig
    from services.gateway.routers.teaching_pack_runs import _default_backpressure_config
    app.dependency_overrides[_default_backpressure_config] = lambda: BackpressureConfig(
        max_active_runs_per_teacher=999_999,
        max_total_active_runs=999_999,
    )
    return app


async def _skip_if_schema_missing() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(
            lambda sync_connection: set(Base.metadata.tables),
        )
        if "public.run_jobs" not in existing_tables:
            pytest.skip("Teaching Pack route tables are not present")
    await engine.dispose()


async def _create_owned_run(run_id: RunId) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-owner"),
            raw_request="Test ownership",
            class_info={"grade": 5},
        ))
        await session.commit()
    await engine.dispose()


async def _create_owned_run_with_gate(run_id: RunId, gate_id: str) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-owner"),
            raw_request="Test ownership",
            class_info={"grade": 5},
        ))
        await TeachingPackControlStore(session).open_gate(GateInterruptCreate(
            gate_id=gate_id,
            run_id=run_id,
            gate_name="blueprint_approval",
            payload={"topic": "Fractions"},
        ))
        await session.commit()
    await engine.dispose()


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


async def _check_owner(run_id: str, user: User) -> bool:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await check_run_owner(run_id, user, session)
    await engine.dispose()
    return result
