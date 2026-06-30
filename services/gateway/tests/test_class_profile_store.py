from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from common.contracts.class_profile import ClassProfile
from services.gateway.class_profile_store import ClassProfileStore
from services.gateway.models import Base, ClassProfileModel, Run, RunStatus, UnitRole
from services.gateway.purge import purge_expired_class_profiles

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    database_engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with database_engine.begin() as connection:
        existing_tables = await connection.run_sync(lambda sync_connection: set(Base.metadata.tables))
        if "public.class_profiles" not in existing_tables:
            pytest.skip("class_profiles table is not present — run alembic upgrade head")
    yield database_engine
    await database_engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()


class TestClassProfileStore:
    async def test_create_read_update_scoped_to_teacher(self, session: AsyncSession) -> None:
        profile_id = f"class-profile-{uuid4()}"
        teacher_id = f"teacher-{uuid4()}"
        store = ClassProfileStore(session)

        await store.create_profile(
            class_profile_id=profile_id,
            teacher_id=teacher_id,
            profile=_profile(class_id="5a", class_size=30),
        )
        await session.commit()

        own_profile = await store.get_profile(profile_id, teacher_id)
        other_profile = await store.get_profile(profile_id, "other-teacher")

        assert own_profile is not None
        assert own_profile.class_size == 30
        assert other_profile is None

        updated = await store.update_profile(
            class_profile_id=profile_id,
            teacher_id=teacher_id,
            profile=_profile(class_id="5a", class_size=24),
        )
        await session.commit()

        assert updated is not None
        assert updated.class_size == 24

        await _delete_profile(session, profile_id)

    async def test_write_scrubs_pii_before_persistence(self, session: AsyncSession) -> None:
        profile_id = f"class-profile-{uuid4()}"
        teacher_id = f"teacher-{uuid4()}"
        store = ClassProfileStore(session)

        await store.create_profile(
            class_profile_id=profile_id,
            teacher_id=teacher_id,
            profile=_profile(class_id="5a", gaps=["Contact Jane Smith at jane@example.com"]),
        )
        await session.commit()

        result = await session.execute(
            select(ClassProfileModel).where(ClassProfileModel.class_profile_id == profile_id)
        )
        row = result.scalar_one()
        serialized = str(row.profile_json)

        assert "jane@example.com" not in serialized
        assert "Jane Smith" not in serialized
        assert "[REDACTED_EMAIL_1]" in serialized

        await _delete_profile(session, profile_id)

    async def test_unit_snapshot_is_immutable_after_source_profile_update(self, session: AsyncSession) -> None:
        profile_id = f"class-profile-{uuid4()}"
        teacher_id = f"teacher-{uuid4()}"
        parent_run_id = f"unit-parent-{uuid4()}"
        store = ClassProfileStore(session)

        await store.create_profile(
            class_profile_id=profile_id,
            teacher_id=teacher_id,
            profile=_profile(class_id="5a", class_size=30),
        )
        session.add(_parent_run(parent_run_id, teacher_id))
        await session.flush()

        snapshot = await store.snapshot_for_unit(
            class_profile_id=profile_id,
            teacher_id=teacher_id,
            parent_run_id=parent_run_id,
        )
        await store.update_profile(
            class_profile_id=profile_id,
            teacher_id=teacher_id,
            profile=_profile(class_id="5a", class_size=18),
        )
        await session.commit()

        result = await session.execute(select(Run).where(Run.run_id == parent_run_id))
        run = result.scalar_one()

        assert snapshot is not None
        assert run.persona_snapshot is not None
        assert run.persona_snapshot["class_size"] == 30

        await session.execute(delete(Run).where(Run.run_id == parent_run_id))
        await _delete_profile(session, profile_id)

    async def test_expired_soft_deleted_profiles_are_purged(self, session: AsyncSession) -> None:
        profile_id = f"class-profile-{uuid4()}"
        teacher_id = f"teacher-{uuid4()}"
        store = ClassProfileStore(session)

        await store.create_profile(
            class_profile_id=profile_id,
            teacher_id=teacher_id,
            profile=_profile(class_id="5a"),
        )
        await session.flush()
        result = await session.execute(
            select(ClassProfileModel).where(ClassProfileModel.class_profile_id == profile_id)
        )
        row = result.scalar_one()
        row.deleted_at = datetime.now(UTC) - timedelta(days=400)
        row.retention_days = 1
        await session.commit()

        purged = await purge_expired_class_profiles(session)
        await session.commit()

        assert profile_id in purged


class TestClassProfilesMigration:
    async def test_table_and_index_exist(self, engine: AsyncEngine) -> None:
        async with engine.connect() as connection:
            columns = await connection.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "AND table_name = 'class_profiles' "
                "AND column_name IN "
                "('class_profile_id', 'teacher_id', 'profile_json', 'schema_version', "
                "'created_at', 'updated_at', 'deleted_at', 'retention_days')",
            ))
            index_row = await connection.execute(text(
                "SELECT indexname FROM pg_indexes "
                "WHERE schemaname = 'public' "
                "AND tablename = 'class_profiles' "
                "AND indexname = 'ix_class_profiles_teacher_id'",
            ))

        assert set(columns.scalars().all()) == {
            "class_profile_id",
            "teacher_id",
            "profile_json",
            "schema_version",
            "created_at",
            "updated_at",
            "deleted_at",
            "retention_days",
        }
        assert index_row.scalar_one_or_none() == "ix_class_profiles_teacher_id"


def _profile(
    *,
    class_id: str,
    class_size: int = 30,
    gaps: list[str] | None = None,
) -> ClassProfile:
    return ClassProfile(
        class_id=class_id,
        grade="Grade 5",
        age_band="upper_primary",
        subject_focus="math",
        language="vi",
        class_size=class_size,
        proficiency_level="developing",
        prior_knowledge_gaps=gaps or [],
    )


def _parent_run(run_id: str, teacher_id: str) -> Run:
    return Run(
        run_id=run_id,
        teacher_id=teacher_id,
        status=RunStatus.PENDING,
        current_step=1,
        raw_request="Plan a unit about fractions",
        class_info={"grade": 5, "subject": "math"},
        unit_role=UnitRole.UNIT_PARENT,
        lesson_sequence={"sessions": []},
    )


async def _delete_profile(session: AsyncSession, profile_id: str) -> None:
    await session.execute(
        delete(ClassProfileModel).where(ClassProfileModel.class_profile_id == profile_id)
    )
    await session.commit()
