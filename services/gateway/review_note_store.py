"""Anchored review notes on V2 artifact-document versions (ADR-055)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from sqlalchemy import select

from services.gateway.artifact_document_models import ReviewNoteRecord
from services.gateway.models import utc_now

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from services.gateway.teaching_pack_types import RunId

type ReviewNoteStatus = Literal["open", "resolved"]


@dataclass(frozen=True, slots=True)
class ReviewNoteCreate:
    note_id: str
    run_id: RunId
    artifact_id: str
    document_id: str
    author_id: str
    body: str
    blocking: bool
    content_entity_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReviewNoteRead:
    note_id: str
    artifact_id: str
    document_id: str
    content_entity_id: str | None
    author_id: str
    body: str
    blocking: bool
    status: ReviewNoteStatus


class ReviewNoteNotFoundError(LookupError):
    def __init__(self, note_id: str) -> None:
        self.note_id = note_id
        super().__init__(note_id)


class ReviewNoteStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, note: ReviewNoteCreate) -> ReviewNoteRead:
        record = ReviewNoteRecord(
            note_id=note.note_id,
            run_id=note.run_id,
            artifact_id=note.artifact_id,
            document_id=note.document_id,
            content_entity_id=note.content_entity_id,
            author_id=note.author_id,
            body=note.body,
            blocking=note.blocking,
            status="open",
        )
        self._session.add(record)
        await self._session.flush()
        return _to_read(record)

    async def list_for_artifact(self, run_id: RunId, artifact_id: str) -> list[ReviewNoteRead]:
        statement = (
            select(ReviewNoteRecord)
            .where(ReviewNoteRecord.run_id == run_id, ReviewNoteRecord.artifact_id == artifact_id)
            .order_by(ReviewNoteRecord.created_at.desc())
        )
        records = (await self._session.execute(statement)).scalars().all()
        return [_to_read(record) for record in records]

    async def resolve(self, note_id: str) -> ReviewNoteRead:
        record = await self._session.get(ReviewNoteRecord, note_id)
        if record is None:
            raise ReviewNoteNotFoundError(note_id)
        record.status = "resolved"
        record.resolved_at = utc_now()
        await self._session.flush()
        return _to_read(record)

    async def has_open_blocking(self, run_id: RunId, artifact_id: str) -> bool:
        statement = select(ReviewNoteRecord.note_id).where(
            ReviewNoteRecord.run_id == run_id,
            ReviewNoteRecord.artifact_id == artifact_id,
            ReviewNoteRecord.blocking.is_(True),
            ReviewNoteRecord.status == "open",
        )
        return (await self._session.execute(statement)).first() is not None


def _to_read(record: ReviewNoteRecord) -> ReviewNoteRead:
    return ReviewNoteRead(
        note_id=record.note_id,
        artifact_id=record.artifact_id,
        document_id=record.document_id,
        content_entity_id=record.content_entity_id,
        author_id=record.author_id,
        body=record.body,
        blocking=record.blocking,
        status=record.status,  # type: ignore[arg-type]
    )
