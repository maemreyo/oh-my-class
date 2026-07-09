from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base
from services.gateway.teaching_session.roster import (
    RosterImportError,
    get_roster_entry,
    import_roster,
    list_roster,
    parse_roster_csv,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


class TestParseRosterCsv:
    def test_parses_name_and_student_id(self) -> None:
        rows = parse_roster_csv("name,student_id\nAlice,S1\nBob,S2\n")
        assert rows == [("Alice", "S1"), ("Bob", "S2")]

    def test_student_id_is_optional(self) -> None:
        rows = parse_roster_csv("name\nAlice\nBob\n")
        assert rows == [("Alice", None), ("Bob", None)]

    def test_blank_names_are_skipped(self) -> None:
        rows = parse_roster_csv("name,student_id\nAlice,S1\n,S2\n")
        assert rows == [("Alice", "S1")]

    def test_missing_name_column_raises(self) -> None:
        with pytest.raises(RosterImportError):
            parse_roster_csv("student_id\nS1\n")


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    database_engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with database_engine.begin() as connection:
        existing_tables = await connection.run_sync(
            lambda sync_connection: set(Base.metadata.tables),
        )
        if "public.class_roster_entries" not in existing_tables:
            pytest.skip("class_roster_entries table is not present — run alembic upgrade head")
    yield database_engine
    await database_engine.dispose()


@pytest.fixture
async def db(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()


class TestImportRoster:
    """Amendment #4: CSV roster import scoped to `class_id`."""

    async def test_import_persists_rows_scoped_to_class_id(self, db: AsyncSession) -> None:
        class_id = f"class-{uuid4()}"

        entries = await import_roster(
            db, class_id=class_id, imported_by="teacher-1",
            csv_text="name,student_id\nAlice,S1\nBob,S2\n",
        )
        await db.commit()

        assert {e.name for e in entries} == {"Alice", "Bob"}
        assert all(e.class_id == class_id for e in entries)

    async def test_list_roster_is_scoped_to_class_id(self, db: AsyncSession) -> None:
        class_a = f"class-{uuid4()}"
        class_b = f"class-{uuid4()}"
        await import_roster(db, class_id=class_a, csv_text="name\nAlice\n", imported_by="teacher-1")
        await import_roster(db, class_id=class_b, csv_text="name\nCarol\n", imported_by="teacher-1")
        await db.commit()

        roster_a = await list_roster(db, class_id=class_a)
        assert [r.name for r in roster_a] == ["Alice"]

    async def test_reimport_replaces_the_prior_roster(self, db: AsyncSession) -> None:
        class_id = f"class-{uuid4()}"
        await import_roster(
            db, class_id=class_id, csv_text="name\nAlice\nBob\n", imported_by="teacher-1",
        )
        await db.commit()

        await import_roster(
            db, class_id=class_id, csv_text="name\nCarol\n", imported_by="teacher-1",
        )
        await db.commit()

        roster = await list_roster(db, class_id=class_id)
        assert [r.name for r in roster] == ["Carol"]


class TestGetRosterEntry:
    """The authenticated-roster join mode looks up entries through this, scoped to `class_id`."""

    async def test_finds_entry_scoped_to_its_own_class(self, db: AsyncSession) -> None:
        class_id = f"class-{uuid4()}"
        [entry] = await import_roster(
            db, class_id=class_id, imported_by="teacher-1", csv_text="name,student_id\nAlice,S1\n",
        )
        await db.commit()

        found = await get_roster_entry(db, class_id=class_id, roster_entry_id=entry.roster_entry_id)

        assert found is not None
        assert found.name == "Alice"

    async def test_returns_none_for_a_different_class(self, db: AsyncSession) -> None:
        class_id = f"class-{uuid4()}"
        other_class_id = f"class-{uuid4()}"
        [entry] = await import_roster(
            db, class_id=class_id, imported_by="teacher-1", csv_text="name\nAlice\n",
        )
        await db.commit()

        found = await get_roster_entry(
            db, class_id=other_class_id, roster_entry_id=entry.roster_entry_id,
        )

        assert found is None
