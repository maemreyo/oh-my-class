from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.media_asset_store import MediaAssetStore
from services.gateway.media_storage import build_storage_key, sanitize_extension
from services.gateway.models import Base, MediaAssetModel

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    database_engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with database_engine.begin() as connection:
        existing_tables = await connection.run_sync(lambda sync_connection: set(Base.metadata.tables))
        if "public.media_assets" not in existing_tables:
            pytest.skip("media_assets table is not present — run alembic upgrade head")
    yield database_engine
    await database_engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()


class TestMediaAssetStore:
    async def test_create_and_get_scoped_to_owning_teacher(self, session: AsyncSession) -> None:
        teacher_id = f"teacher-{uuid4()}"
        store = MediaAssetStore(session)

        created = await store.create_asset(
            asset_id=f"media-{uuid4()}",
            teacher_id=teacher_id,
            filename="frog-lifecycle.png",
            content_type="image/png",
            storage_key=build_storage_key(teacher_id, "asset-1", "png"),
            tags=["biology", "diagram"],
        )
        await session.commit()

        fetched = await store.get_asset(created.asset_id, teacher_id)
        assert fetched is not None
        assert fetched.filename == "frog-lifecycle.png"
        assert fetched.alt_text is None  # SDX-04 integration point defaults to None

        await _delete_asset(session, created.asset_id)

    async def test_cross_teacher_isolation_get_asset_returns_none(self, session: AsyncSession) -> None:
        """Security-critical: a different teacher must never be able to read
        another teacher's asset by ID, even knowing its exact asset_id."""
        owner_id = f"teacher-{uuid4()}"
        intruder_id = f"teacher-{uuid4()}"
        store = MediaAssetStore(session)

        created = await store.create_asset(
            asset_id=f"media-{uuid4()}",
            teacher_id=owner_id,
            filename="private-lesson-diagram.svg",
            content_type="image/svg+xml",
            storage_key=build_storage_key(owner_id, "asset-2", "svg"),
            tags=[],
        )
        await session.commit()

        as_owner = await store.get_asset(created.asset_id, owner_id)
        as_intruder = await store.get_asset(created.asset_id, intruder_id)

        assert as_owner is not None
        assert as_intruder is None

        await _delete_asset(session, created.asset_id)

    async def test_cross_teacher_isolation_list_assets_never_leaks(self, session: AsyncSession) -> None:
        """Security-critical: listing must never surface another teacher's
        rows, even when both teachers have assets with overlapping tags."""
        teacher_a = f"teacher-{uuid4()}"
        teacher_b = f"teacher-{uuid4()}"
        store = MediaAssetStore(session)

        asset_a = await store.create_asset(
            asset_id=f"media-{uuid4()}",
            teacher_id=teacher_a,
            filename="a-only.png",
            content_type="image/png",
            storage_key=build_storage_key(teacher_a, "asset-a", "png"),
            tags=["shared-tag"],
        )
        asset_b = await store.create_asset(
            asset_id=f"media-{uuid4()}",
            teacher_id=teacher_b,
            filename="b-only.png",
            content_type="image/png",
            storage_key=build_storage_key(teacher_b, "asset-b", "png"),
            tags=["shared-tag"],
        )
        await session.commit()

        list_a = await store.list_assets(teacher_a)
        list_b = await store.list_assets(teacher_b)

        assert [row.asset_id for row in list_a] == [asset_a.asset_id]
        assert [row.asset_id for row in list_b] == [asset_b.asset_id]

        await _delete_asset(session, asset_a.asset_id)
        await _delete_asset(session, asset_b.asset_id)

    async def test_filename_search_filters_within_owner_scope(self, session: AsyncSession) -> None:
        teacher_id = f"teacher-{uuid4()}"
        store = MediaAssetStore(session)

        frog = await store.create_asset(
            asset_id=f"media-{uuid4()}",
            teacher_id=teacher_id,
            filename="frog-lifecycle.png",
            content_type="image/png",
            storage_key=build_storage_key(teacher_id, "asset-frog", "png"),
            tags=["biology"],
        )
        volcano = await store.create_asset(
            asset_id=f"media-{uuid4()}",
            teacher_id=teacher_id,
            filename="volcano-diagram.png",
            content_type="image/png",
            storage_key=build_storage_key(teacher_id, "asset-volcano", "png"),
            tags=["geology"],
        )
        await session.commit()

        by_name = await store.list_assets(teacher_id, q="frog")
        by_tag = await store.list_assets(teacher_id, tag="geology")

        assert [row.asset_id for row in by_name] == [frog.asset_id]
        assert [row.asset_id for row in by_tag] == [volcano.asset_id]

        await _delete_asset(session, frog.asset_id)
        await _delete_asset(session, volcano.asset_id)

    async def test_set_alt_text_is_scoped_and_fills_the_sdx04_hook(self, session: AsyncSession) -> None:
        owner_id = f"teacher-{uuid4()}"
        intruder_id = f"teacher-{uuid4()}"
        store = MediaAssetStore(session)

        created = await store.create_asset(
            asset_id=f"media-{uuid4()}",
            teacher_id=owner_id,
            filename="chart.png",
            content_type="image/png",
            storage_key=build_storage_key(owner_id, "asset-chart", "png"),
            tags=[],
        )
        await session.commit()

        blocked = await store.set_alt_text(created.asset_id, intruder_id, "hijacked")
        updated = await store.set_alt_text(created.asset_id, owner_id, "Bar chart of rainfall by month")
        await session.commit()

        assert blocked is None
        assert updated is not None
        assert updated.alt_text == "Bar chart of rainfall by month"

        await _delete_asset(session, created.asset_id)


class TestMediaAssetsMigration:
    async def test_table_and_index_exist(self, engine: AsyncEngine) -> None:
        async with engine.connect() as connection:
            columns = await connection.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "AND table_name = 'media_assets' "
                "AND column_name IN "
                "('asset_id', 'teacher_id', 'filename', 'content_type', "
                "'storage_key', 'tags', 'alt_text', 'created_at')",
            ))
            index_row = await connection.execute(text(
                "SELECT indexname FROM pg_indexes "
                "WHERE schemaname = 'public' "
                "AND tablename = 'media_assets' "
                "AND indexname = 'ix_media_assets_teacher_id'",
            ))

        assert set(columns.scalars().all()) == {
            "asset_id",
            "teacher_id",
            "filename",
            "content_type",
            "storage_key",
            "tags",
            "alt_text",
            "created_at",
        }
        assert index_row.scalar_one_or_none() == "ix_media_assets_teacher_id"


def test_storage_key_scheme_is_flat_and_teacher_scoped_not_run_scoped() -> None:
    """AC4: keys must be `teacher-media/{teacher_id}/{asset_id}.{ext}`, never
    `runs/{run_id}/media/...` — this is what lets a future trust-lifecycle/003
    migration be additive instead of a rewrite."""
    key = build_storage_key("teacher-42", "media-abc", "png")

    assert key == "teacher-media/teacher-42/media-abc.png"
    assert not key.startswith("runs/")


def test_sanitize_extension_rejects_path_traversal_and_unusual_input() -> None:
    assert sanitize_extension("photo.PNG") == "png"
    assert sanitize_extension("no-extension") == "bin"
    assert sanitize_extension("evil../../etc/passwd") == "bin"


async def _delete_asset(session: AsyncSession, asset_id: str) -> None:
    await session.execute(delete(MediaAssetModel).where(MediaAssetModel.asset_id == asset_id))
    await session.commit()
