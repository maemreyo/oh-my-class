"""Persistence for teacher-handled Visual Source Suggestions (ADR-056)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import select

from common.contracts.visual_source_suggestion import VisualSourceSuggestion
from services.gateway.media_asset_version_models import VisualSourceSuggestionRecord

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class VisualSourceSuggestionNotFoundError(LookupError):
    def __init__(self, suggestion_id: str) -> None:
        self.suggestion_id = suggestion_id
        super().__init__(suggestion_id)


class VisualSourceSuggestionNotPendingError(ValueError):
    def __init__(self, suggestion_id: str, status: str) -> None:
        self.suggestion_id = suggestion_id
        self.status = status
        super().__init__(f"{suggestion_id} is {status!r}, not pending")


class VisualSourceSuggestionStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, run_id: str, description: str, candidate_url: str | None, license_hint: str | None,
    ) -> VisualSourceSuggestion:
        record = VisualSourceSuggestionRecord(
            suggestion_id=f"suggestion-{uuid4().hex[:16]}",
            run_id=run_id,
            description=description,
            candidate_url=candidate_url,
            license_hint=license_hint,
            status="pending",
        )
        self._session.add(record)
        await self._session.flush()
        return _to_contract(record)

    async def list_for_run(self, run_id: str) -> list[VisualSourceSuggestion]:
        statement = (
            select(VisualSourceSuggestionRecord)
            .where(VisualSourceSuggestionRecord.run_id == run_id)
            .order_by(VisualSourceSuggestionRecord.created_at.desc())
        )
        records = (await self._session.execute(statement)).scalars().all()
        return [_to_contract(r) for r in records]

    async def get(self, suggestion_id: str) -> VisualSourceSuggestion | None:
        record = await self._session.get(VisualSourceSuggestionRecord, suggestion_id)
        return _to_contract(record) if record is not None else None

    async def convert(self, suggestion_id: str, converted_asset_id: str) -> VisualSourceSuggestion:
        """Mark a suggestion converted once the teacher has actually uploaded a
        licensed Media Asset Version -- never before. The `candidate_url` is
        never fetched or embedded by this call or any other."""
        record = await self._require_pending(suggestion_id)
        record.status = "converted"
        record.converted_asset_id = converted_asset_id
        await self._session.flush()
        return _to_contract(record)

    async def dismiss(self, suggestion_id: str) -> VisualSourceSuggestion:
        record = await self._require_pending(suggestion_id)
        record.status = "dismissed"
        await self._session.flush()
        return _to_contract(record)

    async def _require_pending(self, suggestion_id: str) -> VisualSourceSuggestionRecord:
        record = await self._session.get(VisualSourceSuggestionRecord, suggestion_id)
        if record is None:
            raise VisualSourceSuggestionNotFoundError(suggestion_id)
        if record.status != "pending":
            raise VisualSourceSuggestionNotPendingError(suggestion_id, record.status)
        return record


def _to_contract(record: VisualSourceSuggestionRecord) -> VisualSourceSuggestion:
    return VisualSourceSuggestion(
        suggestion_id=record.suggestion_id,
        run_id=record.run_id,
        description=record.description,
        candidate_url=record.candidate_url,
        license_hint=record.license_hint,
        status=record.status,  # type: ignore[arg-type]
        converted_asset_id=record.converted_asset_id,
    )
