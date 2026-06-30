from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from services.gateway.models import Base, Run, RunStatus
from services.gateway.outcome_models import DeliveryRecordModel
from services.gateway.outcome_delivery import SqlAlchemyOutcomeDeliverySink
from services.gateway.teaching_pack_completion import TeachingPackCompletionRecorder
from services.gateway.teaching_pack_types import RunId

from .test_teaching_pack_completion import RecordingExportWriter, RecordingFailureStore

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    database_engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    try:
        async with database_engine.begin() as connection:
            existing_tables = await connection.run_sync(lambda sync_conn: set(Base.metadata.tables))
            if "public.delivery_records" not in existing_tables:
                pytest.skip("delivery_records table is not present — run alembic upgrade head")
        yield database_engine
    except (OSError, SQLAlchemyError) as exc:
        pytest.skip(f"Postgres is unavailable for outcome delivery hook test: {exc}")
    finally:
        await database_engine.dispose()


@pytest.fixture
async def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def test_completed_export_writes_delivery_record_without_blocking_run(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = RunId(f"run-delivery-{uuid4()}")
    teacher_id = "teacher-1"
    async with session_factory() as session:
        session.add(Run(
            run_id=run_id,
            teacher_id=teacher_id,
            status=RunStatus.PENDING,
            current_step=1,
            raw_request="delivery hook test",
        ))
        await session.commit()

    store = RecordingFailureStore()
    recorder = TeachingPackCompletionRecorder(
        store,
        export_writer=RecordingExportWriter(),
        outcome_delivery=SqlAlchemyOutcomeDeliverySink(session_factory),
    )
    state = {
        "run_id": run_id,
        "exported_files": ["exports/run-delivery/snapshot.html"],
        "contract": {"class_id": "class-5A"},
        "artifacts": [{"kc_ids": ["KC-fractions", "KC-equivalent"]}],
    }

    try:
        await recorder.persist_completion(run_id, state)

        async with session_factory() as session:
            result = await session.execute(
                select(DeliveryRecordModel).where(DeliveryRecordModel.run_id == run_id),
            )
            delivery = result.scalar_one()

        assert delivery.teacher_id == teacher_id
        assert delivery.class_id == "class-5A"
        assert delivery.kc_ids == ["KC-fractions", "KC-equivalent"]
        assert store.transitions[-1].status is RunStatus.COMPLETED
    finally:
        async with session_factory() as session:
            await session.execute(delete(Run).where(Run.run_id == run_id))
            await session.commit()
