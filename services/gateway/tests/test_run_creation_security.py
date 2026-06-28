from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base, Run
from services.gateway.teaching_pack_types import TeacherId
from services.gateway.run_creation import create_teaching_pack_run_record

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(
            lambda sync_connection: set(Base.metadata.tables),
        )
        if "public.runs" not in existing_tables:
            pytest.skip("Teaching Pack run tables are not present")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()


async def test_create_run_record_persists_minimized_class_info(
    session: AsyncSession,
) -> None:
    result = await create_teaching_pack_run_record(
        session,
        teacher_id=TeacherId("teacher-security"),
        raw_request="Teach fractions",
        class_info={
            "grade": 5,
            "subject": "math",
            "student_evidence": {
                "name": "Mai Nguyen",
                "email": "mai@example.com",
                "score": 42,
                "misconceptions": ["equivalent fractions"],
            },
        },
        request_hash="hash",
        idempotency_key=None,
    )

    stored = await session.scalar(select(Run).where(Run.run_id == result.run_id))

    assert stored is not None
    class_info = stored.class_info
    assert class_info is not None
    assert class_info["student_evidence"] == {
        "misconceptions": ["equivalent fractions"],
    }
    await session.execute(delete(Run).where(Run.run_id == result.run_id))
    await session.commit()
