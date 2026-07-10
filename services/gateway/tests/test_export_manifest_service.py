"""#452: capability-checked export creation and explicit regeneration."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from common.contracts.teaching_pack_capabilities import (
    CapabilityStatus,
    load_teaching_pack_capabilities,
)
from services.gateway import export_manifest_service
from services.gateway.export_manifest_service import (
    ExportFormatNotImplementedError,
    UnsupportedExportPairError,
    create_export_record_checked,
    regenerate_stale_exports,
)
from services.gateway.models import Run, RunStatus
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
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()


async def _make_run_and_snapshot(session: AsyncSession, *, artifact_type: str = "lesson") -> RunId:
    run_id = RunId(f"export-svc-{uuid4()}")
    session.add(Run(
        run_id=run_id,
        teacher_id=TeacherId("teacher-export-svc"),
        status=RunStatus.COMPLETED,
        current_step=1,
        raw_request="Test export manifest service",
        class_info={"grade": 5},
    ))
    await session.flush()
    await TeachingPackSnapshotStore(session).create_snapshot(ArtifactSnapshotCreate(
        snapshot_id=f"snap-{uuid4()}",
        run_id=run_id,
        artifact_id="artifact-1",
        artifact_type=artifact_type,
        content_json={"title": "Fractions"},
        rendered_html="<!DOCTYPE html><html><body>fractions lesson</body></html>",
        renderer_version="1.0",
    ))
    return run_id


async def test_create_export_record_checked_rejects_unsupported_pair_before_persisting(
    session: AsyncSession,
) -> None:
    run_id = await _make_run_and_snapshot(session, artifact_type="lesson")
    manifest = load_teaching_pack_capabilities()
    store = TeachingPackExportStore(session)

    with pytest.raises(UnsupportedExportPairError):
        await create_export_record_checked(
            store,
            manifest,
            ExportRecordCreate(
                export_id=f"export-{uuid4()}",
                run_id=run_id,
                artifact_id="artifact-1",
                snapshot_id="snap-x",
                format="not-a-real-format",
                storage_path="somewhere",
            ),
            "lesson",
        )

    assert await store.list_exports(run_id) == []
    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()


async def test_create_export_record_checked_stamps_capability_version(session: AsyncSession) -> None:
    run_id = await _make_run_and_snapshot(session, artifact_type="lesson")
    head = await TeachingPackSnapshotStore(session).get_latest_snapshot(run_id, "artifact-1")
    assert head is not None
    manifest = load_teaching_pack_capabilities()
    store = TeachingPackExportStore(session)

    record = await create_export_record_checked(
        store,
        manifest,
        ExportRecordCreate(
            export_id=f"export-{uuid4()}",
            run_id=run_id,
            artifact_id="artifact-1",
            snapshot_id=head.snapshot_id,
            format="html",
            storage_path=f"exports/{head.snapshot_id}.html",
        ),
        "lesson",
    )

    assert record.capability_version == manifest.manifest_version
    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()


async def test_regenerate_only_rewrites_stale_formats_and_reuses_the_rest(
    session: AsyncSession, tmp_path: Path,
) -> None:
    run_id = await _make_run_and_snapshot(session, artifact_type="lesson")
    snapshot_store = TeachingPackSnapshotStore(session)
    head = await snapshot_store.get_latest_snapshot(run_id, "artifact-1")
    assert head is not None
    export_store = TeachingPackExportStore(session)
    await export_store.create_export_record(ExportRecordCreate(
        export_id=f"export-{uuid4()}",
        run_id=run_id,
        artifact_id="artifact-1",
        snapshot_id=head.snapshot_id,
        format="html",
        storage_path="already-current.html",
    ))

    result = await regenerate_stale_exports(
        session,
        run_id=run_id,
        artifact_id="artifact-1",
        artifact_type="lesson",
        head=head,
        formats=["html"],
        base_dir=tmp_path,
    )

    assert result.regenerated == []
    assert result.reused == ["html"]
    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()


async def test_regenerate_rewrites_a_genuinely_stale_format_with_a_new_immutable_record(
    session: AsyncSession, tmp_path: Path,
) -> None:
    run_id = await _make_run_and_snapshot(session, artifact_type="lesson")
    snapshot_store = TeachingPackSnapshotStore(session)
    stale_head = await snapshot_store.get_latest_snapshot(run_id, "artifact-1")
    assert stale_head is not None
    export_store = TeachingPackExportStore(session)
    await export_store.create_export_record(ExportRecordCreate(
        export_id=f"export-{uuid4()}",
        run_id=run_id,
        artifact_id="artifact-1",
        snapshot_id=stale_head.snapshot_id,
        format="html",
        storage_path="stale.html",
    ))
    # An edit lands: a new snapshot for the same artifact -- the export above is now stale.
    await snapshot_store.create_snapshot(ArtifactSnapshotCreate(
        snapshot_id=f"snap-{uuid4()}",
        run_id=run_id,
        artifact_id="artifact-1",
        artifact_type="lesson",
        content_json={"title": "Fractions v2"},
        rendered_html="<!DOCTYPE html><html><body>updated fractions lesson</body></html>",
        renderer_version="1.0",
    ))
    new_head = await snapshot_store.get_latest_snapshot(run_id, "artifact-1")
    assert new_head is not None

    result = await regenerate_stale_exports(
        session,
        run_id=run_id,
        artifact_id="artifact-1",
        artifact_type="lesson",
        head=new_head,
        formats=["html"],
        base_dir=tmp_path,
    )

    assert result.regenerated == ["html"]
    assert result.reused == []
    latest = await export_store.get_latest_export_for_format(run_id, "artifact-1", "html")
    assert latest is not None
    assert latest.snapshot_id == new_head.snapshot_id
    assert latest.capability_version is not None
    # the older export record is untouched, still reachable.
    all_exports = await export_store.list_exports(run_id, artifact_id="artifact-1")
    assert stale_head.snapshot_id in {e.snapshot_id for e in all_exports}
    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()


async def test_regenerate_raises_for_a_format_with_no_writer_implementation(
    session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defense-in-depth guard: a manifest that *does* declare a pair supported
    must still have a real writer registered, or this must fail loudly rather
    than write mislabeled HTML into a .gift file. Forces gift's writer set
    empty via monkeypatch so this stays true regardless of which formats
    #454-458 have actually wired by the time this test runs."""
    monkeypatch.setattr(export_manifest_service, "_NODE_BRIDGE_FORMATS", frozenset())
    run_id = await _make_run_and_snapshot(session, artifact_type="lesson")
    snapshot_store = TeachingPackSnapshotStore(session)
    head = await snapshot_store.get_latest_snapshot(run_id, "artifact-1")
    assert head is not None
    export_store = TeachingPackExportStore(session)
    await export_store.create_export_record(ExportRecordCreate(
        export_id=f"export-{uuid4()}",
        run_id=run_id,
        artifact_id="artifact-1",
        snapshot_id=head.snapshot_id,
        format="gift",
        storage_path="old.gift.txt",
    ))
    await snapshot_store.create_snapshot(ArtifactSnapshotCreate(
        snapshot_id=f"snap-{uuid4()}",
        run_id=run_id,
        artifact_id="artifact-1",
        artifact_type="lesson",
        content_json={"title": "Fractions v2"},
        rendered_html="<!DOCTYPE html><html><body>updated</body></html>",
        renderer_version="1.0",
    ))
    head = await snapshot_store.get_latest_snapshot(run_id, "artifact-1")
    assert head is not None
    manifest_declaring_gift_supported = load_teaching_pack_capabilities().model_copy(update={
        "exports": tuple(
            e.model_copy(update={"status": CapabilityStatus.SUPPORTED, "supported_artifact_types": ("lesson",)})
            if e.export_format == "gift" else e
            for e in load_teaching_pack_capabilities().exports
        ),
    })

    with pytest.raises(ExportFormatNotImplementedError):
        await regenerate_stale_exports(
            session,
            run_id=run_id,
            artifact_id="artifact-1",
            artifact_type="lesson",
            head=head,
            formats=["gift"],
            manifest=manifest_declaring_gift_supported,
            base_dir=tmp_path,
        )
    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()


async def test_regenerate_writes_a_real_gift_file_for_a_quiz_artifact(
    session: AsyncSession, tmp_path: Path,
) -> None:
    """#454: gift now has a real writer -- exercise it end to end through the
    node CLI bridge rather than only asserting it no longer raises."""
    run_id = RunId(f"export-svc-{uuid4()}")
    session.add(Run(
        run_id=run_id,
        teacher_id=TeacherId("teacher-export-svc"),
        status=RunStatus.COMPLETED,
        current_step=1,
        raw_request="Test gift export",
        class_info={"grade": 5},
    ))
    await session.flush()
    quiz_content = {
        "sections": [{
            "questions": [{
                "id": "q1",
                "type": "multiple_choice_single",
                "stem": "2 + 2 = ?",
                "options": [
                    {"text": "3", "isCorrect": False},
                    {"text": "4", "isCorrect": True},
                ],
            }],
        }],
    }
    snapshot_store = TeachingPackSnapshotStore(session)
    await snapshot_store.create_snapshot(ArtifactSnapshotCreate(
        snapshot_id=f"snap-{uuid4()}",
        run_id=run_id,
        artifact_id="artifact-1",
        artifact_type="quiz",
        content_json=quiz_content,
        rendered_html="<!DOCTYPE html><html><body>quiz</body></html>",
        renderer_version="1.0",
    ))
    head = await snapshot_store.get_latest_snapshot(run_id, "artifact-1")
    assert head is not None

    result = await regenerate_stale_exports(
        session,
        run_id=run_id,
        artifact_id="artifact-1",
        artifact_type="quiz",
        head=head,
        formats=["gift"],
        base_dir=tmp_path,
    )

    assert result.regenerated == ["gift"]
    export_store = TeachingPackExportStore(session)
    latest = await export_store.get_latest_export_for_format(run_id, "artifact-1", "gift")
    assert latest is not None
    written = Path(latest.storage_path).read_text(encoding="utf-8")
    assert "2 + 2" in written
    assert "=4" in written
    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()


async def test_regenerate_writes_a_real_h5p_package_for_a_quiz_artifact(
    session: AsyncSession, tmp_path: Path,
) -> None:
    """#455: h5p now has a real writer -- exercise it end to end through the
    node CLI bridge and confirm a real H5P (zip) package is written."""
    run_id = RunId(f"export-svc-{uuid4()}")
    session.add(Run(
        run_id=run_id,
        teacher_id=TeacherId("teacher-export-svc"),
        status=RunStatus.COMPLETED,
        current_step=1,
        raw_request="Test h5p export",
        class_info={"grade": 5},
    ))
    await session.flush()
    quiz_content = {
        "sections": [{
            "questions": [{
                "id": "q1",
                "type": "multiple_choice_single",
                "stem": "2 + 2 = ?",
                "options": [
                    {"text": "3", "isCorrect": False},
                    {"text": "4", "isCorrect": True},
                ],
            }],
        }],
    }
    snapshot_store = TeachingPackSnapshotStore(session)
    await snapshot_store.create_snapshot(ArtifactSnapshotCreate(
        snapshot_id=f"snap-{uuid4()}",
        run_id=run_id,
        artifact_id="artifact-1",
        artifact_type="quiz",
        content_json=quiz_content,
        rendered_html="<!DOCTYPE html><html><body>quiz</body></html>",
        renderer_version="1.0",
    ))
    head = await snapshot_store.get_latest_snapshot(run_id, "artifact-1")
    assert head is not None

    result = await regenerate_stale_exports(
        session,
        run_id=run_id,
        artifact_id="artifact-1",
        artifact_type="quiz",
        head=head,
        formats=["h5p"],
        base_dir=tmp_path,
    )

    assert result.regenerated == ["h5p"]
    export_store = TeachingPackExportStore(session)
    latest = await export_store.get_latest_export_for_format(run_id, "artifact-1", "h5p")
    assert latest is not None
    written = Path(latest.storage_path).read_bytes()
    assert written[:2] == b"PK"  # H5P packages are zip archives
    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()


async def _make_flashcard_run_and_snapshot(session: AsyncSession) -> tuple[RunId, ArtifactSnapshotRead]:
    run_id = RunId(f"export-svc-{uuid4()}")
    session.add(Run(
        run_id=run_id,
        teacher_id=TeacherId("teacher-export-svc"),
        status=RunStatus.COMPLETED,
        current_step=1,
        raw_request="Test flashcard export",
        class_info={"grade": 5},
    ))
    await session.flush()
    snapshot_store = TeachingPackSnapshotStore(session)
    await snapshot_store.create_snapshot(ArtifactSnapshotCreate(
        snapshot_id=f"snap-{uuid4()}",
        run_id=run_id,
        artifact_id="artifact-1",
        artifact_type="flashcard_deck",
        content_json={
            "cards": [
                {"id": "c1", "front": "Photosynthesis", "back": "How plants make food from light"},
            ],
            "subject": "science",
            "gradeLevel": "5",
        },
        rendered_html="<!DOCTYPE html><html><body>flashcards</body></html>",
        renderer_version="1.0",
    ))
    head = await snapshot_store.get_latest_snapshot(run_id, "artifact-1")
    assert head is not None
    return run_id, head


async def test_regenerate_writes_a_real_anki_apkg_for_a_flashcard_deck(
    session: AsyncSession, tmp_path: Path,
) -> None:
    """#457: anki_apkg now has a real writer -- exercise it end to end."""
    run_id, head = await _make_flashcard_run_and_snapshot(session)

    result = await regenerate_stale_exports(
        session,
        run_id=run_id,
        artifact_id="artifact-1",
        artifact_type="flashcard_deck",
        head=head,
        formats=["anki_apkg"],
        base_dir=tmp_path,
    )

    assert result.regenerated == ["anki_apkg"]
    export_store = TeachingPackExportStore(session)
    latest = await export_store.get_latest_export_for_format(run_id, "artifact-1", "anki_apkg")
    assert latest is not None
    written = Path(latest.storage_path).read_bytes()
    assert written[:2] == b"PK"  # .apkg is a zip archive containing a SQLite collection
    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()


async def test_regenerate_writes_a_real_flashcard_tsv_for_a_flashcard_deck(
    session: AsyncSession, tmp_path: Path,
) -> None:
    """#457: flashcard_tsv now has a real writer -- exercise it end to end."""
    run_id, head = await _make_flashcard_run_and_snapshot(session)

    result = await regenerate_stale_exports(
        session,
        run_id=run_id,
        artifact_id="artifact-1",
        artifact_type="flashcard_deck",
        head=head,
        formats=["flashcard_tsv"],
        base_dir=tmp_path,
    )

    assert result.regenerated == ["flashcard_tsv"]
    export_store = TeachingPackExportStore(session)
    latest = await export_store.get_latest_export_for_format(run_id, "artifact-1", "flashcard_tsv")
    assert latest is not None
    written = Path(latest.storage_path).read_text(encoding="utf-8")
    assert "Photosynthesis" in written
    assert "How plants make food from light" in written
    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()
