"""Shared fixtures for deterministic E2E tests.

All tests use an in-memory SQLite-style async engine backed by PostgreSQL
(tests rely on a running DB via DATABASE_URL).  LLM calls are mocked at
the store level — no real API traffic.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, AsyncIterator
from uuid import uuid4

import pytest
from sqlalchemy import delete, event, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from services.gateway.models import Base, Run, RunStatus
from services.gateway.pipeline_v2_models import (
    ArtifactSnapshot,
    GateInterrupt,
    RunEvent,
    RunStatusHistory,
)
from services.gateway.pipeline_v2_store import (
    PipelineV2EventCreate,
    PipelineV2RunCreate,
    PipelineV2RunStore,
    PipelineV2StatusTransition,
)
from services.gateway.pipeline_v2_types import RunId, TeacherId

if TYPE_CHECKING:
    pass

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def db_engine():
    """Create an async engine for E2E tests."""
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    # Verify tables exist
    async with engine.begin() as conn:
        existing = await conn.run_sync(
            lambda c: set(Base.metadata.tables.keys()),
        )
        if "runs" not in existing:
            pytest.skip("Pipeline V2 tables are not present")
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(db_engine) -> AsyncIterator[AsyncSession]:
    """Yield a session that rolls back after each test."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as db:
        yield db
        await db.rollback()


@pytest.fixture
def teacher_id() -> TeacherId:
    return TeacherId(f"teacher-e2e-{uuid4().hex[:8]}")


@pytest.fixture
def run_id() -> RunId:
    return RunId(f"run-e2e-{uuid4()}")


async def create_test_run(
    session: AsyncSession,
    *,
    run_id: RunId,
    teacher_id: TeacherId,
    status: RunStatus = RunStatus.PENDING,
    raw_request: str = "Teach fractions to Grade 5",
    class_info: dict | None = None,
) -> None:
    """Insert a minimal Run row for testing."""
    run = Run(
        run_id=run_id,
        teacher_id=teacher_id,
        status=status,
        current_step=1,
        raw_request=raw_request,
        class_info=class_info or {"grade": 5, "subject": "math"},
        artifact_types=[],
        theme="default",
        quality_passed=False,
        teacher_approved=False,
        revision_count=0,
        export_formats=["html"],
        tokens_used=1234,
        cost_usd=0.042,
    )
    session.add(run)
    await session.flush()


async def create_test_events(
    session: AsyncSession,
    *,
    run_id: RunId,
    events: list[dict],
) -> None:
    """Insert RunEvent rows. Each dict needs: event_name, stage (optional)."""
    for i, evt in enumerate(events, start=1):
        event_row = RunEvent(
            run_id=run_id,
            sequence=i,
            event_name=evt["event_name"],
            stage=evt.get("stage"),
            visibility=evt.get("visibility", "teacher"),
            payload=evt.get("payload"),
        )
        session.add(event_row)
    await session.flush()


async def create_test_snapshot(
    session: AsyncSession,
    *,
    snapshot_id: str,
    run_id: RunId,
    artifact_id: str = "art-1",
    content_hash: str | None = None,
) -> None:
    """Insert a minimal ArtifactSnapshot row."""
    if content_hash is None:
        content_hash = hashlib.sha256(snapshot_id.encode()).hexdigest()[:16]
    snapshot = ArtifactSnapshot(
        snapshot_id=snapshot_id,
        run_id=run_id,
        artifact_id=artifact_id,
        artifact_type="worksheet",
        content_hash=content_hash,
        html_hash=f"html-{content_hash[:8]}",
        content_json={"title": "Test"},
        rendered_html="<html>test</html>",
        student_rendered_html="<html>student</html>",
        renderer_version="1.0",
        template_version="1.0",
        theme_version="1.0",
        standalone_valid=True,
    )
    session.add(snapshot)
    await session.flush()
