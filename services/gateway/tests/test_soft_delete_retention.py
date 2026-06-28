"""Tests for soft-delete, retention, purge, and schema versioning.

Requires a running PostgreSQL instance (DATABASE_URL).
Follows the same integration-test pattern as test_teaching_pack_runs_router.py.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
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
from services.gateway.purge import purge_expired_runs, purge_student_evidence
from services.gateway.retention import RetentionConfig, get_retention_days, is_expired
from services.gateway.routers.teaching_pack_runs import router
from services.gateway.schema_version import (
    SCHEMA_VERSION,
    VersionedContract,
    migrate_contract,
    validate_schema_version,
)
from services.gateway.soft_delete import is_run_deleted, soft_delete_run
from services.gateway.teaching_pack_control_store import (
    GateInterruptCreate,
    TeachingPackControlStore,
)
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_models import GateInterrupt, GateResponse, RunJob
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
        user_id="teacher-test",
        username="teacher-test",
        role=Role.TEACHER,
    )
    app.dependency_overrides[get_teaching_pack_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Soft-delete unit tests
# ---------------------------------------------------------------------------


class TestSoftDeleteRun:
    def test_soft_delete_sets_deleted_at_and_deleted_by(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_create_test_run, run_id)

        response = client.delete(f"/teaching-packs/run/{run_id}")
        assert response.status_code == 202
        assert response.json()["deleted"] is True

        run = anyio.run(_get_run, run_id)
        assert run is not None
        assert run.deleted_at is not None
        assert run.deleted_by == "teacher-test"
        anyio.run(_cleanup_run, run_id)

    def test_soft_deleted_run_hidden_from_status(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_create_test_run, run_id)
        anyio.run(_soft_delete_run_direct, run_id, "teacher-test")

        response = client.get(f"/teaching-packs/run/{run_id}/status?replay_only=true")
        assert response.status_code == 404
        anyio.run(_cleanup_run, run_id)

    def test_resume_on_deleted_run_returns_404(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_run_with_gate, run_id, gate_id)
        anyio.run(_soft_delete_run_direct, run_id, "teacher-test")

        response = client.post(
            f"/teaching-packs/run/{run_id}/resume",
            json={
                "gate_id": gate_id,
                "gate_name": "blueprint_approval",
                "action": "approve",
                "response": {},
            },
        )
        assert response.status_code == 404
        anyio.run(_cleanup_run, run_id)

    def test_restore_makes_run_visible_again(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_create_test_run, run_id)
        anyio.run(_soft_delete_run_direct, run_id, "teacher-test")

        assert anyio.run(_check_is_deleted, run_id) is True

        response = client.post(f"/teaching-packs/run/{run_id}/restore")
        assert response.status_code == 202
        assert response.json()["restored"] is True

        assert anyio.run(_check_is_deleted, run_id) is False
        anyio.run(_cleanup_run, run_id)


# ---------------------------------------------------------------------------
# Hard purge tests
# ---------------------------------------------------------------------------


class TestHardPurge:
    def test_purge_removes_expired_runs(self) -> None:
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_create_test_run, run_id)
        # Set deleted_at far in the past (past retention window)
        anyio.run(_set_deleted_at, run_id, datetime.now(UTC) - timedelta(days=400))

        purged = anyio.run(_run_purge)
        assert run_id in purged

        run = anyio.run(_get_run, run_id)
        assert run is None

    def test_purge_preserves_non_expired_runs(self) -> None:
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_create_test_run, run_id)
        # Set deleted_at recently (within retention window)
        anyio.run(_set_deleted_at, run_id, datetime.now(UTC) - timedelta(days=10))

        purged = anyio.run(_run_purge)
        assert run_id not in purged

        run = anyio.run(_get_run, run_id)
        assert run is not None
        anyio.run(_cleanup_run, run_id)

    def test_purge_preserves_non_deleted_runs(self) -> None:
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_create_test_run, run_id)

        purged = anyio.run(_run_purge)
        assert run_id not in purged

        run = anyio.run(_get_run, run_id)
        assert run is not None
        anyio.run(_cleanup_run, run_id)


# ---------------------------------------------------------------------------
# Retention config tests
# ---------------------------------------------------------------------------


class TestRetentionConfig:
    def test_defaults_are_correct(self) -> None:
        config = RetentionConfig()
        assert config.run_metadata == 365
        assert config.student_evidence == 30
        assert config.artifacts == 180
        assert config.events == 90
        assert config.snapshots == 180

    def test_get_retention_days_returns_correct_defaults(self) -> None:
        assert get_retention_days("run_metadata") == 365
        assert get_retention_days("student_evidence") == 30
        assert get_retention_days("artifacts") == 180
        assert get_retention_days("events") == 90
        assert get_retention_days("snapshots") == 180

    def test_get_retention_days_raises_for_unknown_class(self) -> None:
        with pytest.raises(KeyError):
            get_retention_days("nonexistent_class")

    def test_is_expired_false_when_not_deleted(self) -> None:
        assert is_expired(None, 30) is False

    def test_is_expired_false_within_window(self) -> None:
        deleted_at = datetime.now(UTC) - timedelta(days=5)
        assert is_expired(deleted_at, 30) is False

    def test_is_expired_true_past_window(self) -> None:
        deleted_at = datetime.now(UTC) - timedelta(days=31)
        assert is_expired(deleted_at, 30) is True

    def test_as_dict_round_trip(self) -> None:
        config = RetentionConfig()
        d = config.as_dict()
        assert d["run_metadata"] == 365
        assert d["student_evidence"] == 30


# ---------------------------------------------------------------------------
# Student evidence minimization tests
# ---------------------------------------------------------------------------


class TestStudentEvidenceMinimization:
    def test_purge_student_evidence_redacts_pii(self) -> None:
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_create_test_run_with_evidence, run_id, {
            "name": "Alice",
            "email": "alice@example.com",
            "performance": "good",
        })
        anyio.run(_backdate_created_at, run_id, datetime.now(UTC) - timedelta(days=40))

        redacted = anyio.run(_run_purge_student_evidence)
        assert redacted >= 1

        run = anyio.run(_get_run, run_id)
        assert run is not None
        evidence = run.class_info.get("student_evidence", {})
        assert "name" not in evidence
        assert "email" not in evidence
        assert evidence.get("performance") == "good"
        anyio.run(_cleanup_run, run_id)


# ---------------------------------------------------------------------------
# Schema version tests
# ---------------------------------------------------------------------------


class TestSchemaVersion:
    def test_current_version_is_valid(self) -> None:
        assert validate_schema_version(SCHEMA_VERSION) is True

    def test_validate_accepts_current_version(self) -> None:
        assert validate_schema_version("1.0") is True

    def test_validate_accepts_previous_v2_version(self) -> None:
        assert validate_schema_version("0.9") is True

    def test_validate_rejects_future_version(self) -> None:
        assert validate_schema_version("9.0") is False

    def test_validate_rejects_unknown_version(self) -> None:
        assert validate_schema_version("abc") is False

    def test_migrate_contract_1_0_to_1_0_is_noop(self) -> None:
        data = {"title": "Test", "schema_version": "1.0"}
        result = migrate_contract(data, "1.0", "1.0")
        assert result == data

    def test_migrate_contract_0_9_to_1_0_adapts_draft_fields(self) -> None:
        data = {"schema_version": "0.9", "artifacts": ["lesson"], "language": "vi"}

        result = migrate_contract(data, "0.9", "1.0")

        assert result["schema_version"] == "1.0"
        assert result["artifact_types"] == ["lesson"]
        assert result["instruction_language"] == "vi"

    def test_migrate_contract_rejects_unknown_source(self) -> None:
        with pytest.raises(ValueError, match="Unsupported source version"):
            migrate_contract({}, "9.0", "1.0")

    def test_migrate_contract_rejects_unknown_target(self) -> None:
        with pytest.raises(ValueError, match="Unsupported target version"):
            migrate_contract({}, "1.0", "9.0")

    def test_versioned_contract_protocol(self) -> None:
        class Good:
            schema_version = "1.0"

        assert isinstance(Good(), VersionedContract)

        class Bad:
            pass

        assert not isinstance(Bad(), VersionedContract)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _skip_if_schema_missing() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(
            lambda sync_connection: set(Base.metadata.tables),
        )
        if "public.runs" not in existing_tables:
            pytest.skip("Teaching Pack tables are not present")
    await engine.dispose()


async def _get_session():
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


async def _create_test_run(run_id: RunId) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-test"),
            raw_request="Test run",
            class_info={"grade": 5},
        ))
        await session.commit()
    await engine.dispose()


async def _create_test_run_with_evidence(run_id: RunId, evidence: dict) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-test"),
            raw_request="Test run with evidence",
            class_info={"grade": 5, "student_evidence": evidence},
        ))
        await session.commit()
    await engine.dispose()


async def _create_run_with_gate(run_id: RunId, gate_id: str) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-test"),
            raw_request="Test run with gate",
            class_info={"grade": 5},
        ))
        await TeachingPackControlStore(session).open_gate(GateInterruptCreate(
            gate_id=gate_id,
            run_id=run_id,
            gate_name="blueprint_approval",
            payload={"topic": "Test"},
        ))
        await session.commit()
    await engine.dispose()


async def _get_run(run_id: RunId) -> Run | None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        statement = select(Run).where(Run.run_id == run_id)
        result = await session.execute(statement)
        run = result.scalar_one_or_none()
        # Detach from session before engine disposal
        if run is not None:
            session.expunge(run)
    await engine.dispose()
    return run


async def _set_deleted_at(run_id: RunId, deleted_at: datetime) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        statement = select(Run).where(Run.run_id == run_id).with_for_update()
        result = await session.execute(statement)
        run = result.scalar_one()
        run.deleted_at = deleted_at
        run.deleted_by = "test-purge"
        await session.commit()
    await engine.dispose()


async def _soft_delete_run_direct(run_id: RunId, deleted_by: str) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await soft_delete_run(run_id, deleted_by, session)
        await session.commit()
    await engine.dispose()


async def _cleanup_run(run_id: RunId) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(delete(GateResponse).where(GateResponse.run_id == run_id))
        await session.execute(delete(GateInterrupt).where(GateInterrupt.run_id == run_id))
        await session.execute(delete(RunJob).where(RunJob.run_id == run_id))
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()
    await engine.dispose()


async def _run_purge() -> list[str]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await purge_expired_runs(session)
        await session.commit()
    await engine.dispose()
    return result


async def _run_purge_student_evidence() -> int:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await purge_student_evidence(session)
        await session.commit()
    await engine.dispose()
    return result


async def _check_is_deleted(run_id: RunId) -> bool:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await is_run_deleted(run_id, session)
    await engine.dispose()
    return result


async def _backdate_created_at(run_id: RunId, created_at: datetime) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        statement = select(Run).where(Run.run_id == run_id).with_for_update()
        result = await session.execute(statement)
        run = result.scalar_one()
        run.created_at = created_at.replace(tzinfo=None) if created_at.tzinfo else created_at
        await session.commit()
    await engine.dispose()
