from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.budget import BudgetLedger, record_retry, record_usage
from services.gateway.budget_db import (
    budget_ledger_payload,
    load_budget_ledger,
    save_budget_ledger,
    write_budget_ledger_event,
)
from services.gateway.models import Base
from services.gateway.teaching_pack_models import TeachingPackEventVisibility
from services.gateway.teaching_pack_store import TeachingPackEventCreate
from services.gateway.teaching_pack_types import RunId

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
            lambda sync_connection: Base.metadata.create_all(
                sync_connection,
                checkfirst=True,
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

    def test_budget_ledger_payload_is_replay_safe_json(self) -> None:
        ledger = BudgetLedger(
            tokens_used=25,
            searches_used=2,
            fetches_used=3,
            retries_used={"artifact-1": 1},
        )

        assert budget_ledger_payload(ledger) == {
            "tokens_used": 25,
            "searches_used": 2,
            "fetches_used": 3,
            "retries_used": {"artifact-1": 1},
        }

    async def test_write_budget_ledger_event_records_internal_event(self) -> None:
        store = RecordingBudgetEventStore()
        ledger = BudgetLedger(tokens_used=25, searches_used=2)

        await write_budget_ledger_event(store, run_id=RunId("budget-event"), ledger=ledger)

        assert store.events == [TeachingPackEventCreate(
            run_id=RunId("budget-event"),
            event_name="teaching_pack.budget.ledger_recorded",
            visibility=TeachingPackEventVisibility.INTERNAL,
            payload={
                "tokens_used": 25,
                "searches_used": 2,
                "fetches_used": 0,
                "retries_used": {},
            },
        )]


class RecordingBudgetEventStore:
    def __init__(self) -> None:
        self.events: list[TeachingPackEventCreate] = []

    async def write_event(self, payload: TeachingPackEventCreate) -> None:
        self.events.append(payload)
