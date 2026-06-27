from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.budget import BudgetLedger, record_retry, record_usage
from services.gateway.budget_db import BudgetLedgerRecord, load_budget_ledger, save_budget_ledger
from services.gateway.pipeline_v2_types import RunId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync_connection: BudgetLedgerRecord.__table__.create(
                sync_connection, checkfirst=True,
            ),
        )
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()


class TestBudgetDb:
    async def test_saved_ledger_survives_new_session(self, session: AsyncSession) -> None:
        run_id = RunId(f"budget-{uuid4()}")
        ledger = record_retry(
            record_usage(record_usage(BudgetLedger(), "tokens", 125), "searches"),
            "artifact-1",
        )

        await save_budget_ledger(session, run_id=run_id, ledger=ledger)
        await session.commit()
        loaded = await load_budget_ledger(session, run_id)

        assert loaded.tokens_used == 125
        assert loaded.searches_used == 1
        assert loaded.retries_used == {"artifact-1": 1}

    async def test_missing_ledger_loads_empty_budget(self, session: AsyncSession) -> None:
        loaded = await load_budget_ledger(session, RunId(f"missing-{uuid4()}"))

        assert loaded == BudgetLedger()

    async def test_save_budget_ledger_updates_existing_row(self, session: AsyncSession) -> None:
        run_id = RunId(f"budget-{uuid4()}")
        await save_budget_ledger(session, run_id=run_id, ledger=BudgetLedger(tokens_used=10))
        await save_budget_ledger(session, run_id=run_id, ledger=BudgetLedger(tokens_used=20))
        await session.commit()
        loaded = await load_budget_ledger(session, run_id)

        assert loaded.tokens_used == 20
