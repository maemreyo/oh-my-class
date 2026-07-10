from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base, Run, RunStatus
from services.gateway.teaching_pack_export_models import ExportRecord
from services.gateway.teaching_pack_export_store import ExportRecordCreate, TeachingPackExportStore
from services.gateway.teaching_pack_snapshot_store import (
    ArtifactSnapshotCreate,
    TeachingPackSnapshotStore,
)
from services.gateway.teaching_pack_types import RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        existing = await connection.run_sync(lambda sync_connection: set(Base.metadata.tables))
        if "public.export_records" not in existing:
            pytest.skip("export_records table is not present (run alembic upgrade head)")
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()


async def _make_run(session: AsyncSession) -> RunId:
    run_id = RunId(f"export-store-{uuid4()}")
    session.add(Run(
        run_id=run_id,
        teacher_id=TeacherId("teacher-export"),
        status=RunStatus.COMPLETED,
        current_step=1,
        raw_request="Test export store",
        class_info={"grade": 5},
    ))
    await session.flush()
    return run_id


async def _make_snapshot(session: AsyncSession, run_id: RunId, artifact_id: str, snapshot_id: str) -> None:
    # Content varies per snapshot_id -- create_snapshot dedupes by content
    # hash, so identical content across snapshot_ids would silently collapse
    # onto the first row instead of creating a distinct one.
    store = TeachingPackSnapshotStore(session)
    await store.create_snapshot(ArtifactSnapshotCreate(
        snapshot_id=snapshot_id,
        run_id=run_id,
        artifact_id=artifact_id,
        artifact_type="slide_deck",
        content_json={"title": f"Deck {snapshot_id}"},
        rendered_html=f"<!DOCTYPE html><html><body>{snapshot_id}</body></html>",
        renderer_version="1.0",
    ))


class TestTeachingPackExportStore:
    async def test_export_record_persists_source_snapshot_id(self, session: AsyncSession) -> None:
        run_id = await _make_run(session)
        await _make_snapshot(session, run_id, "artifact-1", "snap-1")
        store = TeachingPackExportStore(session)

        record = await store.create_export_record(ExportRecordCreate(
            export_id=f"export-{uuid4()}",
            run_id=run_id,
            artifact_id="artifact-1",
            snapshot_id="snap-1",
            format="pptx",
            storage_path=f"exports/{run_id}/snap-1.pptx",
        ))

        assert record.snapshot_id == "snap-1"
        fetched = await store.list_exports(run_id)
        assert [item.export_id for item in fetched] == [record.export_id]
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()

    async def test_edit_does_not_touch_or_delete_existing_export_records(
        self, session: AsyncSession,
    ) -> None:
        """SDE-06 AC1: a new snapshot (an "edit") must never cascade into
        deleting/modifying a prior export_records row."""
        run_id = await _make_run(session)
        await _make_snapshot(session, run_id, "artifact-1", "snap-1")
        store = TeachingPackExportStore(session)
        record = await store.create_export_record(ExportRecordCreate(
            export_id=f"export-{uuid4()}",
            run_id=run_id,
            artifact_id="artifact-1",
            snapshot_id="snap-1",
            format="pptx",
            storage_path=f"exports/{run_id}/snap-1.pptx",
        ))

        # Simulate an edit: a brand-new snapshot row for the same artifact.
        await _make_snapshot(session, run_id, "artifact-1", "snap-2")

        result = await session.execute(
            select(ExportRecord).where(ExportRecord.export_id == record.export_id),
        )
        untouched = result.scalar_one()
        assert untouched.snapshot_id == "snap-1"
        assert untouched.storage_path == record.storage_path
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()

    async def test_older_export_remains_fetchable_after_newer_edit_and_export(
        self, session: AsyncSession,
    ) -> None:
        """SDE-06 AC4: export v1, then an edit + export v2 -- both remain
        independently reachable/downloadable."""
        run_id = await _make_run(session)
        await _make_snapshot(session, run_id, "artifact-1", "snap-1")
        store = TeachingPackExportStore(session)
        v1 = await store.create_export_record(ExportRecordCreate(
            export_id=f"export-{uuid4()}",
            run_id=run_id,
            artifact_id="artifact-1",
            snapshot_id="snap-1",
            format="pptx",
            storage_path=f"exports/{run_id}/snap-1.pptx",
        ))

        await _make_snapshot(session, run_id, "artifact-1", "snap-2")
        v2 = await store.create_export_record(ExportRecordCreate(
            export_id=f"export-{uuid4()}",
            run_id=run_id,
            artifact_id="artifact-1",
            snapshot_id="snap-2",
            format="pptx",
            storage_path=f"exports/{run_id}/snap-2.pptx",
        ))

        all_exports = await store.list_exports(run_id, artifact_id="artifact-1")
        export_ids = {item.export_id for item in all_exports}
        assert v1.export_id in export_ids
        assert v2.export_id in export_ids
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()

    async def test_is_stale_flags_lagging_export_and_not_current_export(
        self, session: AsyncSession,
    ) -> None:
        run_id = await _make_run(session)
        await _make_snapshot(session, run_id, "artifact-1", "snap-1")
        store = TeachingPackExportStore(session)
        await store.create_export_record(ExportRecordCreate(
            export_id=f"export-{uuid4()}",
            run_id=run_id,
            artifact_id="artifact-1",
            snapshot_id="snap-1",
            format="pptx",
            storage_path=f"exports/{run_id}/snap-1.pptx",
        ))

        # Export matches current head -> not stale.
        assert await store.is_stale(run_id, "artifact-1", "snap-1") is False

        # An edit lands (new head snapshot) but no re-export happens -> stale.
        await _make_snapshot(session, run_id, "artifact-1", "snap-2")
        assert await store.is_stale(run_id, "artifact-1", "snap-2") is True

        # No export at all for an artifact -> not stale (nothing to compare).
        assert await store.is_stale(run_id, "artifact-none", "snap-x") is False

        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()

    async def test_capability_version_is_persisted_and_read_back(self, session: AsyncSession) -> None:
        run_id = await _make_run(session)
        await _make_snapshot(session, run_id, "artifact-1", "snap-1")
        store = TeachingPackExportStore(session)

        record = await store.create_export_record(ExportRecordCreate(
            export_id=f"export-{uuid4()}",
            run_id=run_id,
            artifact_id="artifact-1",
            snapshot_id="snap-1",
            format="html",
            storage_path=f"exports/{run_id}/snap-1.html",
            capability_version="teaching-pack-capabilities.v1",
        ))

        assert record.capability_version == "teaching-pack-capabilities.v1"
        fetched = await store.list_exports(run_id)
        assert fetched[0].capability_version == "teaching-pack-capabilities.v1"
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()

    async def test_stale_formats_flags_only_the_impacted_format(self, session: AsyncSession) -> None:
        """#452 AC2: content changes mark only impacted export entries stale --
        an html export lagging the head must not report a still-current gift
        export (or vice versa) as stale."""
        run_id = await _make_run(session)
        await _make_snapshot(session, run_id, "artifact-1", "snap-1")
        store = TeachingPackExportStore(session)
        await store.create_export_record(ExportRecordCreate(
            export_id=f"export-{uuid4()}",
            run_id=run_id,
            artifact_id="artifact-1",
            snapshot_id="snap-1",
            format="html",
            storage_path=f"exports/{run_id}/snap-1.html",
        ))
        await store.create_export_record(ExportRecordCreate(
            export_id=f"export-{uuid4()}",
            run_id=run_id,
            artifact_id="artifact-1",
            snapshot_id="snap-1",
            format="gift",
            storage_path=f"exports/{run_id}/snap-1.gift.txt",
        ))

        # An edit lands, but only html is re-exported -- gift now lags.
        await _make_snapshot(session, run_id, "artifact-1", "snap-2")
        await store.create_export_record(ExportRecordCreate(
            export_id=f"export-{uuid4()}",
            run_id=run_id,
            artifact_id="artifact-1",
            snapshot_id="snap-2",
            format="html",
            storage_path=f"exports/{run_id}/snap-2.html",
        ))

        stale = await store.stale_formats(run_id, "artifact-1", "snap-2", ["html", "gift"])

        assert stale == ["gift"]
        latest_gift = await store.get_latest_export_for_format(run_id, "artifact-1", "gift")
        assert latest_gift is not None
        assert latest_gift.snapshot_id == "snap-1"
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()
