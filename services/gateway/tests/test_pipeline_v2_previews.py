from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import anyio
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User
from services.gateway.models import Base, Run, RunStatus
from services.gateway.pipeline_v2_db import get_pipeline_v2_session
from services.gateway.pipeline_v2_models import RunEvent
from services.gateway.pipeline_v2_snapshot_models import ArtifactSnapshot
from services.gateway.pipeline_v2_snapshot_store import (
    ArtifactSnapshotCreate,
    PipelineV2SnapshotStore,
)
from services.gateway.pipeline_v2_store import PipelineV2RunCreate, PipelineV2RunStore
from services.gateway.pipeline_v2_types import RunId, TeacherId
from services.gateway.routers.pipeline_v2_previews import router

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
def client() -> Iterator[TestClient]:
    anyio.run(_skip_if_schema_missing)
    app = FastAPI()
    app.include_router(router, prefix="/pipeline-v2")

    async def override_session() -> AsyncIterator[AsyncSession]:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session
        await engine.dispose()

    app.dependency_overrides[require_teacher] = lambda: User(
        user_id="teacher-preview",
        username="teacher-preview",
        role=Role.TEACHER,
    )
    app.dependency_overrides[get_pipeline_v2_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def other_teacher_client() -> Iterator[TestClient]:
    anyio.run(_skip_if_schema_missing)
    app = FastAPI()
    app.include_router(router, prefix="/pipeline-v2")

    async def override_session() -> AsyncIterator[AsyncSession]:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session
        await engine.dispose()

    app.dependency_overrides[require_teacher] = lambda: User(
        user_id="teacher-other",
        username="teacher-other",
        role=Role.TEACHER,
    )
    app.dependency_overrides[get_pipeline_v2_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


class TestPipelineV2Previews:
    def test_metadata_returns_snapshot_refs_without_html(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_snapshot, run_id, snapshot_id)

        response = client.get(f"/pipeline-v2/run/{run_id}/snapshots/{snapshot_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["snapshot_id"] == snapshot_id
        assert data["artifact_id"] == "lesson-1"
        assert data["standalone_valid"] is True
        assert data["renderer_version"] == "renderer@test"
        assert data["template_version"] == "template@test"
        assert data["theme_version"] == "theme@test"
        assert "rendered_html" not in data
        assert "student_rendered_html" not in data
        assert "content_hash" in data
        assert "html_hash" in data
        anyio.run(_delete_run, run_id)

    def test_student_preview_redacts_teacher_only_content(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_snapshot, run_id, snapshot_id)

        response = client.get(f"/pipeline-v2/run/{run_id}/snapshots/{snapshot_id}/preview")

        assert response.status_code == 200
        assert "Student question" in response.text
        assert "&lt;img src=x onerror=alert(1)&gt;" in response.text
        assert "<img src=x onerror=alert(1)>" not in response.text
        assert "Answer Key" not in response.text
        assert "Correct answer" not in response.text
        anyio.run(_delete_run, run_id)

    def test_teacher_preview_includes_answer_keys(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_snapshot, run_id, snapshot_id)

        response = client.get(
            f"/pipeline-v2/run/{run_id}/snapshots/{snapshot_id}/preview?view=teacher",
        )

        assert response.status_code == 200
        assert "Answer Key" in response.text
        assert "Correct answer" in response.text
        anyio.run(_delete_run, run_id)

    def test_approve_records_exact_snapshot_ids_and_event(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_snapshot, run_id, snapshot_id)

        response = client.post(
            f"/pipeline-v2/run/{run_id}/approved-snapshots",
            json={"snapshot_ids": [snapshot_id]},
        )
        approved_event = anyio.run(_approved_event_payload, run_id)

        assert response.status_code == 200
        assert response.json() == {
            "run_id": run_id,
            "approved_snapshot_ids": [snapshot_id],
        }
        assert approved_event == {"snapshot_ids": [snapshot_id]}
        anyio.run(_delete_run, run_id)

    def test_approve_rejects_run_that_is_not_awaiting_approval(
        self,
        client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_snapshot, run_id, snapshot_id, RunStatus.PENDING)

        response = client.post(
            f"/pipeline-v2/run/{run_id}/approved-snapshots",
            json={"snapshot_ids": [snapshot_id]},
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "run_not_awaiting_approval"
        anyio.run(_delete_run, run_id)

    def test_approve_rejects_non_standalone_snapshot(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(
            _create_run_with_snapshot,
            run_id,
            snapshot_id,
            RunStatus.AWAITING_APPROVAL,
            (
                '<!DOCTYPE html><html><head><link href="/style.css"></head>'
                "<body>oh-my-class</body></html>"
            ),
        )

        response = client.post(
            f"/pipeline-v2/run/{run_id}/approved-snapshots",
            json={"snapshot_ids": [snapshot_id]},
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "non_standalone_snapshot"
        anyio.run(_delete_run, run_id)

    def test_non_owner_cannot_access_snapshot(
        self,
        other_teacher_client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_create_run_with_snapshot, run_id, snapshot_id)

        response = other_teacher_client.get(f"/pipeline-v2/run/{run_id}/snapshots/{snapshot_id}")

        assert response.status_code == 404
        assert response.json()["detail"] == "run_not_found"
        anyio.run(_delete_run, run_id)


async def _skip_if_schema_missing() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(
            lambda sync_connection: set(Base.metadata.tables),
        )
        if "public.artifact_snapshots" not in existing_tables:
            pytest.skip("Pipeline V2 snapshot tables are not present")
    await engine.dispose()


async def _create_run_with_snapshot(
    run_id: RunId,
    snapshot_id: str,
    status: RunStatus = RunStatus.AWAITING_APPROVAL,
    rendered_html: str | None = None,
) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await PipelineV2RunStore(session).create_run(PipelineV2RunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-preview"),
            raw_request="Teach rendered preview",
            class_info={"grade": 5},
        ))
        run = await session.get(Run, run_id)
        if run is not None:
            run.status = status
        await PipelineV2SnapshotStore(session).create_snapshot(ArtifactSnapshotCreate(
            snapshot_id=snapshot_id,
            run_id=run_id,
            artifact_id="lesson-1",
            artifact_type="lesson",
            content_json={
                "title": f"Fractions {snapshot_id}",
                "sections": [
                    {
                        "heading": "Question",
                        "content": "Student question <img src=x onerror=alert(1)>",
                    },
                    {
                        "heading": "Answer Key",
                        "content": "Correct answer",
                        "teacher_only": True,
                    },
                ],
            },
            rendered_html=rendered_html or (
                f"<!DOCTYPE html><html><body><h1>Fractions {snapshot_id}</h1>"
                "<section>Student question</section>"
                "<section>Answer Key Correct answer</section></body></html>"
            ),
            renderer_version="renderer@test",
            template_version="template@test",
            theme_version="theme@test",
        ))
        await session.commit()
    await engine.dispose()


async def _approved_event_payload(run_id: RunId):
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(
            select(RunEvent.payload).where(
                RunEvent.run_id == run_id,
                RunEvent.event_name == "pipeline_v2.content.approved_snapshots",
            ),
        )
        payload = result.scalar_one()
    await engine.dispose()
    return payload


async def _delete_run(run_id: RunId) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(delete(ArtifactSnapshot).where(ArtifactSnapshot.run_id == run_id))
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()
    await engine.dispose()
