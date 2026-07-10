"""Persistence for Content Briefs and their append-only strategy review path."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import select

from common.contracts.content_brief import ContentBrief
from services.gateway.content_brief_models import ContentBriefRecord, StrategyReviewRecord
from services.gateway.models import utc_now

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from common.contracts.strategy_review import StrategyChangeRequest, TypedFillFailure


class ContentBriefNotFoundError(LookupError):
    def __init__(self, content_brief_id: str) -> None:
        self.content_brief_id = content_brief_id
        super().__init__(content_brief_id)


class StrategyReviewEntryNotFoundError(LookupError):
    def __init__(self, request_id: str) -> None:
        self.request_id = request_id
        super().__init__(request_id)


class ContentBriefStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, brief: ContentBrief) -> None:
        self._session.add(ContentBriefRecord(
            content_brief_id=brief.content_brief_id,
            run_id=brief.run_id,
            artifact_type=brief.artifact_type,
            brief_json=brief.model_dump(mode="json"),
        ))
        await self._session.flush()

    async def get(self, content_brief_id: str) -> ContentBrief | None:
        record = await self._session.get(ContentBriefRecord, content_brief_id)
        if record is None:
            return None
        return ContentBrief.model_validate(record.brief_json)


class StrategyReviewStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_fill_failure(self, failure: TypedFillFailure) -> str:
        request_id = f"review-{uuid4().hex[:16]}"
        self._session.add(StrategyReviewRecord(
            request_id=request_id,
            content_brief_id=failure.content_brief_id,
            request_type="fill_failure",
            reason_or_kind=failure.reason,
            detail=failure.detail,
        ))
        await self._session.flush()
        return request_id

    async def record_strategy_change_request(self, request: StrategyChangeRequest) -> str:
        request_id = f"review-{uuid4().hex[:16]}"
        self._session.add(StrategyReviewRecord(
            request_id=request_id,
            content_brief_id=request.content_brief_id,
            request_type="strategy_change",
            reason_or_kind=request.change_kind,
            detail=request.rationale,
        ))
        await self._session.flush()
        return request_id

    async def list_for_brief(self, content_brief_id: str) -> list[StrategyReviewRecord]:
        statement = (
            select(StrategyReviewRecord)
            .where(StrategyReviewRecord.content_brief_id == content_brief_id)
            .order_by(StrategyReviewRecord.created_at.asc())
        )
        return list((await self._session.execute(statement)).scalars().all())

    async def resolve(self, request_id: str) -> None:
        record = await self._session.get(StrategyReviewRecord, request_id)
        if record is None:
            raise StrategyReviewEntryNotFoundError(request_id)
        record.status = "resolved"
        record.resolved_at = utc_now()
        await self._session.flush()
