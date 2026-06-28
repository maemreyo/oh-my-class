from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Mapped, mapped_column

from services.gateway.budget import BudgetLedger
from services.gateway.models import Base, utc_now

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from services.gateway.teaching_pack_types import RunId


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
