from __future__ import annotations

from pathlib import Path
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
from services.gateway.teaching_pack_snapshot_store import (
    ArtifactSnapshotCreate,
    TeachingPackSnapshotStore,
)
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


async def _seed_lesson_run_snapshot_and_export(
    run_id: RunId, snapshot_id: str, with_export: bool, new_run: bool = True,
) -> None:
    """Like `_seed_run_snapshot_and_export`, but `lesson`/`html` -- a pair the
    real capability manifest supports (lesson has no export format wired
    beyond html), used for the capability-checked regenerate path tests."""
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
            artifact_type="lesson",
            content_json={"title": f"Lesson {snapshot_id}"},
            rendered_html=f"<!DOCTYPE html><html><body>{snapshot_id}</body></html>",
            renderer_version="1.0",
        ))
        if with_export:
            await TeachingPackExportStore(session).create_export_record(ExportRecordCreate(
                export_id=f"export-{uuid4()}",
                run_id=run_id,
                artifact_id="artifact-1",
                snapshot_id=snapshot_id,
                format="html",
                storage_path=f"exports/{run_id}/{snapshot_id}.html",
            ))
        await session.commit()
    await engine.dispose()


async def _seed_two_approved_artifacts(run_id: RunId) -> None:
    """A lesson + a quiz, both approved -- the minimum shape #453's Teaching
    Pack bundle export needs (it only bundles approved artifacts)."""
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-export"),
            raw_request="Test teaching pack bundle export",
            class_info={"grade": 5, "subject": "Math"},
        ))
        snapshot_store = TeachingPackSnapshotStore(session)
        lesson_snapshot = await snapshot_store.create_snapshot(ArtifactSnapshotCreate(
            snapshot_id=f"snap-{uuid4()}",
            run_id=run_id,
            artifact_id="lesson-1",
            artifact_type="lesson",
            content_json={
                "title": "Intro to Fractions",
                "sections": [
                    {"id": "s1", "type": "objective", "title": "Objective", "content": "Understand fractions"},
                ],
                "metadata": {"subject": "Math", "grade_level": "Grade 5"},
            },
            rendered_html=f"<!DOCTYPE html><html><body>oh-my-class lesson {run_id}</body></html>",
            renderer_version="1.0",
        ))
        quiz_snapshot = await snapshot_store.create_snapshot(ArtifactSnapshotCreate(
            snapshot_id=f"snap-{uuid4()}",
            run_id=run_id,
            artifact_id="quiz-1",
            artifact_type="quiz",
            content_json={
                "title": "Fractions Quiz",
                "sections": [{"id": "q1", "prompt": "What is 1/2 + 1/2?", "options": ["1", "2", "0"]}],
            },
            rendered_html=f"<!DOCTYPE html><html><body>oh-my-class quiz {run_id}</body></html>",
            renderer_version="1.0",
        ))
        await snapshot_store.approve_snapshots(run_id, [lesson_snapshot.snapshot_id, quiz_snapshot.snapshot_id])
        await session.commit()
    await engine.dispose()


async def _export_extra_format(run_id: RunId, snapshot_id: str, export_format: str) -> None:
    """Add one more export row (any format, no capability check) for an
    already-existing snapshot -- used to set up multi-format staleness
    fixtures for the read-only `/export-status/by-format` endpoint, which
    doesn't enforce the capability matrix (only regenerate does)."""
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await TeachingPackExportStore(session).create_export_record(ExportRecordCreate(
            export_id=f"export-{uuid4()}",
            run_id=run_id,
            artifact_id="artifact-1",
            snapshot_id=snapshot_id,
            format=export_format,
            storage_path=f"exports/{run_id}/{snapshot_id}.{export_format}",
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

    def test_export_status_by_format_flags_only_the_impacted_format(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_v1 = f"snap-{uuid4()}"
        anyio.run(_seed_lesson_run_snapshot_and_export, run_id, snapshot_v1, True)
        anyio.run(_export_extra_format, run_id, snapshot_v1, "gift")
        # An edit lands but only html gets re-exported -- gift now lags.
        snapshot_v2 = f"snap-{uuid4()}"
        anyio.run(_seed_lesson_run_snapshot_and_export, run_id, snapshot_v2, False, False)
        anyio.run(_export_extra_format, run_id, snapshot_v2, "html")

        response = client.get(f"/teaching-packs/runs/{run_id}/artifacts/artifact-1/export-status/by-format")
        assert response.status_code == 200
        by_format = {entry["format"]: entry["stale"] for entry in response.json()["formats"]}
        assert by_format == {"html": False, "gift": True}
        anyio.run(delete_run, run_id)

    def test_regenerate_rewrites_only_what_needs_it(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_v1 = f"snap-{uuid4()}"
        anyio.run(_seed_lesson_run_snapshot_and_export, run_id, snapshot_v1, True)
        # An edit lands with no re-export -- the existing html export is now stale.
        snapshot_v2 = f"snap-{uuid4()}"
        anyio.run(_seed_lesson_run_snapshot_and_export, run_id, snapshot_v2, False, False)

        response = client.post(
            f"/teaching-packs/runs/{run_id}/artifacts/artifact-1/exports/regenerate",
            json={"formats": ["html"]},
        )
        assert response.status_code == 200
        assert response.json() == {"regenerated": ["html"], "reused": []}

        # Calling it again immediately: the just-regenerated export is now current.
        again = client.post(
            f"/teaching-packs/runs/{run_id}/artifacts/artifact-1/exports/regenerate",
            json={"formats": ["html"]},
        )
        assert again.json() == {"regenerated": [], "reused": ["html"]}
        anyio.run(delete_run, run_id)

    def test_regenerate_rejects_unsupported_pair(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_seed_lesson_run_snapshot_and_export, run_id, snapshot_id, True)

        response = client.post(
            f"/teaching-packs/runs/{run_id}/artifacts/artifact-1/exports/regenerate",
            json={"formats": ["not-a-real-format"]},
        )
        assert response.status_code == 422
        assert response.json()["detail"]["error"] == "unsupported_export_pair"
        anyio.run(delete_run, run_id)

    def test_regenerate_with_no_prior_exports_and_no_formats_given_is_rejected(
        self, client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_seed_lesson_run_snapshot_and_export, run_id, snapshot_id, False)

        response = client.post(
            f"/teaching-packs/runs/{run_id}/artifacts/artifact-1/exports/regenerate",
            json={},
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "no_formats_to_regenerate"
        anyio.run(delete_run, run_id)

    def test_teaching_pack_bundle_export_combines_every_approved_artifact(
        self, client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_seed_two_approved_artifacts, run_id)

        response = client.post(f"/teaching-packs/runs/{run_id}/exports/teaching-pack")

        assert response.status_code == 200
        data = response.json()
        assert set(data["artifact_ids"]) == {"lesson-1", "quiz-1"}
        written_path = Path(data["storage_path"])
        written = written_path.read_text(encoding="utf-8")
        assert "Intro to Fractions" in written
        assert "Fractions Quiz" in written

        listed = client.get(f"/teaching-packs/runs/{run_id}/exports")
        bundle_records = [e for e in listed.json() if e["artifact_id"] == "__teaching_pack__"]
        assert len(bundle_records) == 1
        assert bundle_records[0]["format"] == "html"

        written_path.unlink()
        written_path.parent.rmdir()
        anyio.run(delete_run, run_id)

    def test_teaching_pack_bundle_export_rejects_a_run_with_no_approved_artifacts(
        self, client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_seed_lesson_run_snapshot_and_export, run_id, snapshot_id, False)

        response = client.post(f"/teaching-packs/runs/{run_id}/exports/teaching-pack")
        assert response.status_code == 422
        assert response.json()["detail"] == "no_approved_artifacts"
        anyio.run(delete_run, run_id)


class TestSignedDownloadUrl:
    """#118: `download_url` is a real presigned URL when the app's export
    writer is object-storage-backed, verified against the real local MinIO
    -- not a mocked S3 client."""

    @pytest.fixture
    def object_storage_client(self, client: TestClient):
        from botocore.exceptions import EndpointConnectionError

        from services.gateway.object_storage import build_s3_client, ensure_bucket_exists, object_storage_config_from_env
        from services.gateway.teaching_pack_export_writer import ObjectStorageTeachingPackExportWriter

        config = object_storage_config_from_env()
        s3_client = build_s3_client(config)
        try:
            ensure_bucket_exists(s3_client, config.bucket)
        except EndpointConnectionError as exc:
            pytest.skip(f"MinIO is unavailable for signed-URL tests: {exc}")
        client.app.state.export_writer = ObjectStorageTeachingPackExportWriter(config=config, client=s3_client)
        return s3_client, config

    def test_list_exports_returns_a_working_signed_url_when_object_storage_backed(
        self, client: TestClient, object_storage_client,
    ) -> None:
        import httpx

        s3_client, config = object_storage_client
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_seed_run_snapshot_and_export, run_id, snapshot_id, True)
        key = f"exports/{run_id}/{snapshot_id}.pptx"
        body = b"fake pptx bytes for signed-url test"
        s3_client.put_object(Bucket=config.bucket, Key=key, Body=body)

        response = client.get(f"/teaching-packs/runs/{run_id}/exports")

        assert response.status_code == 200
        records = response.json()
        assert len(records) == 1
        download_url = records[0]["download_url"]
        assert download_url is not None
        fetched = httpx.get(download_url)
        assert fetched.status_code == 200
        assert fetched.content == body
        anyio.run(delete_run, run_id)

    def test_download_url_is_none_when_export_writer_is_not_object_storage_backed(
        self, client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = f"snap-{uuid4()}"
        anyio.run(_seed_run_snapshot_and_export, run_id, snapshot_id, True)

        response = client.get(f"/teaching-packs/runs/{run_id}/exports")

        assert response.status_code == 200
        assert response.json()[0]["download_url"] is None
        anyio.run(delete_run, run_id)
