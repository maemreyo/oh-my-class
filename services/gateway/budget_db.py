from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import TYPE_CHECKING, Protocol

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Mapped, mapped_column

from services.gateway.budget import BudgetLedger
from services.gateway.models import Base, utc_now
from services.gateway.teaching_pack_models import TeachingPackEventVisibility
from services.gateway.teaching_pack_store import TeachingPackEventCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import JsonObject

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from services.gateway.teaching_pack_types import RunId


class BudgetEventStore(Protocol):
    async def write_event(self, payload: TeachingPackEventCreate) -> object: ...


class BudgetLedgerRecord(Base):
    __tablename__ = "run_budget_ledgers"
    __table_args__ = {"schema": "public"}

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    searches_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fetches_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retries_used: Mapped[dict[str, int] | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now,
    )


async def save_budget_ledger(
    session: AsyncSession,
    *,
    run_id: RunId,
    ledger: BudgetLedger,
) -> None:
    statement = pg_insert(BudgetLedgerRecord).values(
        run_id=run_id,
        tokens_used=ledger.tokens_used,
        searches_used=ledger.searches_used,
        fetches_used=ledger.fetches_used,
        retries_used=ledger.retries_used or None,
    ).on_conflict_do_update(
        index_elements=["run_id"],
        set_={
            "tokens_used": ledger.tokens_used,
            "searches_used": ledger.searches_used,
            "fetches_used": ledger.fetches_used,
            "retries_used": ledger.retries_used or None,
            "updated_at": utc_now(),
        },
    )
    await session.execute(statement)
    await session.flush()


async def save_budget_ledger_with_event(
    session: AsyncSession,
    *,
    run_id: RunId,
    ledger: BudgetLedger,
) -> None:
    await save_budget_ledger(session, run_id=run_id, ledger=ledger)
    await write_budget_ledger_event(TeachingPackRunStore(session), run_id=run_id, ledger=ledger)


async def write_budget_ledger_event(
    store: BudgetEventStore,
    *,
    run_id: RunId,
    ledger: BudgetLedger,
) -> None:
    await store.write_event(TeachingPackEventCreate(
        run_id=run_id,
        event_name="teaching_pack.budget.ledger_recorded",
        visibility=TeachingPackEventVisibility.INTERNAL,
        payload=budget_ledger_payload(ledger),
    ))


def budget_ledger_payload(ledger: BudgetLedger) -> JsonObject:
    retries: JsonObject = {
        artifact_id: count
        for artifact_id, count in ledger.retries_used.items()
    }
    payload: JsonObject = {
        "tokens_used": ledger.tokens_used,
        "searches_used": ledger.searches_used,
        "fetches_used": ledger.fetches_used,
        "retries_used": retries,
    }
    return payload


async def load_budget_ledger(session: AsyncSession, run_id: RunId) -> BudgetLedger:
    record = await session.get(BudgetLedgerRecord, run_id)
    if record is None:
        return BudgetLedger()
    return BudgetLedger(
        tokens_used=record.tokens_used,
        searches_used=record.searches_used,
        fetches_used=record.fetches_used,
        retries_used=record.retries_used or {},
    )
