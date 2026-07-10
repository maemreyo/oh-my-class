from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import anyio
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User
from services.gateway.models import Base
from services.gateway.routers.exports import router
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_export_store import ExportRecordCreate, TeachingPackExportStore
from services.gateway.teaching_pack_snapshot_store import ArtifactSnapshotCreate, TeachingPackSnapshotStore
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId
from services.gateway.tests.teaching_pack_preview_db import DATABASE_URL
from services.gateway.tests.teaching_pack_preview_helpers import delete_run

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession


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
        user_id="teacher-export",
        username="teacher-export",
        role=Role.TEACHER,
    )
    app.dependency_overrides[get_teaching_pack_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


async def _skip_if_schema_missing() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(lambda _: set(Base.metadata.tables))
        if "public.export_records" not in existing_tables:
            pytest.skip("export_records table is not present (run alembic upgrade head)")
    await engine.dispose()


async def _seed_run_snapshot_and_export(
    run_id: RunId, snapshot_id: str, with_export: bool, new_run: bool = True,
) -> None:
    # ponytail: anyio.run only forwards positional args, so this helper takes
    # with_export/new_run positionally rather than keyword-only.
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        if new_run:
            await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
                run_id=run_id,
                teacher_id=TeacherId("teacher-export"),
                raw_request="Test export router",
                class_info={"grade": 5},
            ))
        await TeachingPackSnapshotStore(session).create_snapshot(ArtifactSnapshotCreate(
            snapshot_id=snapshot_id,
            run_id=run_id,
            artifact_id="artifact-1",
            artifact_type="slide_deck",
            content_json={"title": f"Deck {snapshot_id}"},
            rendered_html=f"<!DOCTYPE html><html><body>{snapshot_id}</body></html>",
            renderer_version="1.0",
        ))
        if with_export:
            await TeachingPackExportStore(session).create_export_record(ExportRecordCreate(
                export_id=f"export-{uuid4()}",
                run_id=run_id,
                artifact_id="artifact-1",
                snapshot_id=snapshot_id,
                format="pptx",
                storage_path=f"exports/{run_id}/{snapshot_id}.pptx",
            ))
        await session.commit()
    await engine.dispose()


class TestExportsRouter:
    def test_export_status_not_stale_when_export_matches_head(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_seed_run_snapshot_and_export, run_id, snapshot_id, True)

        response = client.get(f"/teaching-packs/runs/{run_id}/artifacts/artifact-1/export-status")
        assert response.status_code == 200
        data = response.json()
        assert data["stale"] is False
        assert data["current_snapshot_id"] == snapshot_id
        assert data["latest_export"]["snapshot_id"] == snapshot_id
        anyio.run(delete_run, run_id)

    def test_export_status_stale_after_edit_without_reexport(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_seed_run_snapshot_and_export, run_id, snapshot_id, True)

        # An edit lands: a new snapshot for the same artifact, no re-export call.
        edit_snapshot_id = f"snap-{uuid4()}"
        anyio.run(_seed_run_snapshot_and_export, run_id, edit_snapshot_id, False, False)

        response = client.get(f"/teaching-packs/runs/{run_id}/artifacts/artifact-1/export-status")
        assert response.status_code == 200
        data = response.json()
        assert data["stale"] is True
        assert data["current_snapshot_id"] != data["latest_export"]["snapshot_id"]
        anyio.run(delete_run, run_id)

    def test_list_exports_includes_every_export_not_just_latest(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_v1 = f"snap-{uuid4()}"
        anyio.run(_seed_run_snapshot_and_export, run_id, snapshot_v1, True)
        snapshot_v2 = f"snap-{uuid4()}"
        anyio.run(_seed_run_snapshot_and_export, run_id, snapshot_v2, True, False)

        response = client.get(f"/teaching-packs/runs/{run_id}/exports")
        assert response.status_code == 200
        snapshot_ids = {item["snapshot_id"] for item in response.json()}
        assert {snapshot_v1, snapshot_v2}.issubset(snapshot_ids)
        anyio.run(delete_run, run_id)
