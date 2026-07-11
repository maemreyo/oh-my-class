"""#118 (OPS-05): object-storage export writer, verified against the real
local MinIO in `infra/compose/docker-compose.yml` -- not a mocked S3 client
(ADR-032 live-path proof)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from botocore.exceptions import EndpointConnectionError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base, RunStatus
from services.gateway.object_storage import (
    build_s3_client,
    ensure_bucket_exists,
    object_storage_config_from_env,
    presigned_export_url,
)
from services.gateway.teaching_pack_completion import TeachingPackCompletionRecorder
from services.gateway.teaching_pack_export_store import TeachingPackExportStore
from services.gateway.teaching_pack_export_writer import (
    ExportAdapterError,
    ObjectStorageTeachingPackExportWriter,
    export_writer_for_environment,
)
from services.gateway.teaching_pack_export_writer import FileSystemTeachingPackExportWriter
from services.gateway.teaching_pack_snapshot_store import ArtifactSnapshotCreate, TeachingPackSnapshotStore
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore, TeachingPackStatusTransition
from services.gateway.teaching_pack_types import JsonObject, RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@dataclass(frozen=True, slots=True)
class RecordingRenderer:
    rendered_html: str = "<!DOCTYPE html><html><body>oh-my-class object-storage export</body></html>"
    calls: list[JsonObject] = field(default_factory=list)

    async def render(self, artifact: JsonObject) -> str:
        self.calls.append(artifact)
        return self.rendered_html


@pytest.fixture
def s3_client():
    config = object_storage_config_from_env()
    client = build_s3_client(config)
    try:
        ensure_bucket_exists(client, config.bucket)
    except EndpointConnectionError as exc:
        pytest.skip(f"MinIO is unavailable for object-storage export tests: {exc}")
    return client, config


class TestObjectStorageExportWriter:
    @pytest.mark.anyio
    async def test_html_export_round_trips_through_real_minio(self, s3_client) -> None:
        client, config = s3_client
        renderer = RecordingRenderer()
        writer = ObjectStorageTeachingPackExportWriter(config=config, client=client, renderer=renderer)
        run_id = RunId(f"test-object-export-{uuid4()}")
        state = {
            "approved_snapshot_ids": ["snapshot-1"],
            "contract": {"export_formats": ["html"]},
            "rendered_snapshots": [{"snapshot_id": "snapshot-1", "content_json": {"title": "Approved"}}],
        }

        keys = await writer.write_exports(run_id, state)

        assert keys == [f"exports/{run_id}/snapshot-1.html"]
        # Real round-trip: fetch the object back from MinIO and check bytes,
        # not a mocked put_object call.
        stored = client.get_object(Bucket=config.bucket, Key=keys[0])
        assert stored["Body"].read().decode("utf-8") == renderer.rendered_html

    @pytest.mark.anyio
    async def test_rerunning_the_same_export_overwrites_the_same_key_not_a_duplicate(self, s3_client) -> None:
        client, config = s3_client
        run_id = RunId(f"test-object-export-{uuid4()}")
        state = {
            "approved_snapshot_ids": ["snapshot-1"],
            "contract": {"export_formats": ["html"]},
            "rendered_snapshots": [{"snapshot_id": "snapshot-1", "content_json": {"title": "Approved"}}],
        }

        first = ObjectStorageTeachingPackExportWriter(
            config=config, client=client, renderer=RecordingRenderer("<html>v1</html>"),
        )
        second = ObjectStorageTeachingPackExportWriter(
            config=config, client=client, renderer=RecordingRenderer("<html>v2</html>"),
        )

        first_keys = await first.write_exports(run_id, state)
        second_keys = await second.write_exports(run_id, state)

        assert first_keys == second_keys
        stored = client.get_object(Bucket=config.bucket, Key=second_keys[0])
        assert stored["Body"].read().decode("utf-8") == "<html>v2</html>"

    @pytest.mark.anyio
    async def test_signed_url_fetches_the_real_uploaded_object(self, s3_client) -> None:
        import httpx

        client, config = s3_client
        writer = ObjectStorageTeachingPackExportWriter(config=config, client=client, renderer=RecordingRenderer())
        run_id = RunId(f"test-object-export-{uuid4()}")
        state = {
            "approved_snapshot_ids": ["snapshot-1"],
            "contract": {"export_formats": ["html"]},
            "rendered_snapshots": [{"snapshot_id": "snapshot-1", "content_json": {"title": "Approved"}}],
        }
        keys = await writer.write_exports(run_id, state)

        url = presigned_export_url(client, bucket=config.bucket, key=keys[0], expires_in_seconds=60)
        response = httpx.get(url)

        assert response.status_code == 200
        assert response.text == writer.renderer.rendered_html

    @pytest.mark.anyio
    async def test_unsupported_format_fails_closed_before_any_upload(self, s3_client) -> None:
        client, config = s3_client
        writer = ObjectStorageTeachingPackExportWriter(config=config, client=client, renderer=RecordingRenderer())
        run_id = RunId(f"test-object-export-{uuid4()}")
        state = {
            "approved_snapshot_ids": [],
            "contract": {"export_formats": ["google_forms"]},
            "rendered_snapshots": [],
        }

        with pytest.raises(ExportAdapterError, match="google_forms"):
            await writer.write_exports(run_id, state)


class TestExportWriterEnvironmentSelection:
    def test_development_environment_selects_filesystem_writer(self, tmp_path) -> None:
        writer = export_writer_for_environment("development", base_dir=tmp_path)

        assert isinstance(writer, FileSystemTeachingPackExportWriter)

    def test_staging_environment_selects_object_storage_writer(self, s3_client) -> None:
        writer = export_writer_for_environment("staging")

        assert isinstance(writer, ObjectStorageTeachingPackExportWriter)

    def test_production_environment_selects_object_storage_writer(self, s3_client) -> None:
        writer = export_writer_for_environment("production")

        assert isinstance(writer, ObjectStorageTeachingPackExportWriter)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


class TestObjectKeysPersistToExportRecords:
    """#118: 'store keys in DB, not paths' -- proven end-to-end through the
    real completion-recorder + a real Postgres export_records row, not just
    that the writer returns a key-shaped string."""

    @pytest.mark.anyio
    async def test_completion_persists_the_real_object_key_not_a_local_path(
        self, s3_client, db_session: AsyncSession,
    ) -> None:
        client, config = s3_client
        run_id = RunId(f"test-object-export-{uuid4()}")
        await TeachingPackRunStore(db_session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-object-export"),
            raw_request="Build a recap for object-storage export",
            class_info={"grade": 5},
        ))
        await TeachingPackSnapshotStore(db_session).create_snapshot(ArtifactSnapshotCreate(
            snapshot_id="snapshot-1",
            run_id=run_id,
            artifact_id="artifact-1",
            artifact_type="recap",
            content_json={"title": "Recap"},
            rendered_html="<!DOCTYPE html><html><body>oh-my-class recap</body></html>",
            renderer_version="test-renderer@1",
        ))
        await db_session.flush()
        run_store = TeachingPackRunStore(db_session)
        await run_store.transition_status(TeachingPackStatusTransition(
            run_id=run_id, status=RunStatus.AWAITING_APPROVAL, stage=None, reason="test_setup",
        ))

        writer = ObjectStorageTeachingPackExportWriter(config=config, client=client, renderer=RecordingRenderer())
        export_store = TeachingPackExportStore(db_session)
        recorder = TeachingPackCompletionRecorder(
            run_store,
            export_writer=writer,
            export_store=export_store,
        )
        state = {
            "run_id": str(run_id),
            "exported_files": [f"exports/{run_id}/snapshot-1.html"],
            "approved_snapshot_ids": ["snapshot-1"],
            "rendered_snapshots": [{
                "snapshot_id": "snapshot-1",
                "artifact_id": "artifact-1",
                "content_json": {"title": "Recap"},
            }],
        }

        await recorder.persist_completion(run_id, state)

        records = await export_store.list_exports(run_id)
        assert len(records) == 1
        key = records[0].storage_path
        assert key == f"exports/{run_id}/snapshot-1.html"
        # Not just a key-shaped string in the DB -- the object is really there.
        stored = client.get_object(Bucket=config.bucket, Key=key)
        assert stored["Body"].read().decode("utf-8") == writer.renderer.rendered_html
