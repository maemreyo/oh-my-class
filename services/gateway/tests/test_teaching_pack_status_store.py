from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base, Run, RunStatus
from services.gateway.teaching_pack_store import (
    InvalidRunStatusTransitionError,
    TeachingPackRunCreate,
    TeachingPackRunStore,
    TeachingPackStatusTransition,
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
        existing_tables = await connection.run_sync(
            lambda sync_connection: set(Base.metadata.tables),
        )
        if "public.run_status_history" not in existing_tables:
            pytest.skip("Teaching Pack status tables are not present")
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()


class TestTeachingPackStatusStore:
    async def test_transition_status_rejects_invalid_transition(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        store = TeachingPackRunStore(session)
        await store.create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-a"),
            raw_request="Teach rocks",
            class_info={"grade": 4},
        ))

        with pytest.raises(InvalidRunStatusTransitionError, match="transition_not_allowed"):
            await store.transition_status(TeachingPackStatusTransition(
                run_id=run_id,
                status=RunStatus.COMPLETED,
                stage=None,
                reason="skip ahead",
            ))

        await session.rollback()
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()
