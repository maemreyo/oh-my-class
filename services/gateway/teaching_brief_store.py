from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.contracts.teaching_brief import TeachingBrief
from services.gateway.models import TeachingBriefModel


@dataclass(frozen=True, slots=True)
class StoredTeachingBrief:
    brief_id: str
    teacher_id: str
    brief: TeachingBrief


class TeachingBriefStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, brief_id: str, teacher_id: str, brief: TeachingBrief) -> StoredTeachingBrief:
        self._session.add(TeachingBriefModel(
            brief_id=brief_id,
            teacher_id=teacher_id,
            brief_json=brief.model_dump(mode="json"),
        ))
        await self._session.flush()
        return StoredTeachingBrief(brief_id=brief_id, teacher_id=teacher_id, brief=brief)

    async def get(self, brief_id: str, teacher_id: str) -> StoredTeachingBrief | None:
        result = await self._session.execute(select(TeachingBriefModel).where(
            TeachingBriefModel.brief_id == brief_id,
            TeachingBriefModel.teacher_id == teacher_id,
        ))
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return StoredTeachingBrief(
            brief_id=row.brief_id,
            teacher_id=row.teacher_id,
            brief=TeachingBrief.model_validate(row.brief_json),
        )

    async def replace(self, brief_id: str, teacher_id: str, brief: TeachingBrief) -> StoredTeachingBrief | None:
        result = await self._session.execute(select(TeachingBriefModel).where(
            TeachingBriefModel.brief_id == brief_id,
            TeachingBriefModel.teacher_id == teacher_id,
        ).with_for_update())
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.brief_json = brief.model_dump(mode="json")
        await self._session.flush()
        return StoredTeachingBrief(brief_id=row.brief_id, teacher_id=row.teacher_id, brief=brief)
