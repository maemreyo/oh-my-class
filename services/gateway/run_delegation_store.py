"""Explicit, audited reviewer/approval delegation for one run (ADR-051)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import select

from services.gateway.artifact_document_models import RunDelegationRecord

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from services.gateway.teaching_pack_types import RunId


@dataclass(frozen=True, slots=True)
class RunDelegationRead:
    delegation_id: str
    delegate_id: str
    granted_by: str


class RunDelegationStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def grant(self, run_id: RunId, delegate_id: str, granted_by: str) -> RunDelegationRead:
        record = RunDelegationRecord(
            delegation_id=f"delegation-{uuid4().hex[:16]}",
            run_id=run_id,
            delegate_id=delegate_id,
            granted_by=granted_by,
        )
        self._session.add(record)
        await self._session.flush()
        return _to_read(record)

    async def list_for_run(self, run_id: RunId) -> list[RunDelegationRead]:
        statement = select(RunDelegationRecord).where(RunDelegationRecord.run_id == run_id)
        records = (await self._session.execute(statement)).scalars().all()
        return [_to_read(record) for record in records]

    async def is_delegate(self, run_id: RunId, user_id: str) -> bool:
        statement = select(RunDelegationRecord.delegation_id).where(
            RunDelegationRecord.run_id == run_id,
            RunDelegationRecord.delegate_id == user_id,
        )
        return (await self._session.execute(statement)).first() is not None


def _to_read(record: RunDelegationRecord) -> RunDelegationRead:
    return RunDelegationRead(
        delegation_id=record.delegation_id,
        delegate_id=record.delegate_id,
        granted_by=record.granted_by,
    )
