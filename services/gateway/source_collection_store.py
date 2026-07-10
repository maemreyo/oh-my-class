"""Persistence for scoped Source Collections."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from common.contracts.source_collection import SourceCollection, SourceCollectionEntry
from services.gateway.source_collection_models import (
    SourceCollectionEntryRecord,
    SourceCollectionRecord,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class SourceCollectionNotFoundError(LookupError):
    def __init__(self, collection_id: str) -> None:
        self.collection_id = collection_id
        super().__init__(collection_id)


class SourceCollectionStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, collection: SourceCollection) -> None:
        self._session.add(SourceCollectionRecord(
            collection_id=collection.collection_id,
            scope=collection.scope,
            owner_id=collection.owner_id,
        ))
        await self._session.flush()  # parent row must exist before entries reference its FK
        for entry in collection.entries:
            self._add_entry(collection.collection_id, entry)
        await self._session.flush()

    async def add_entry(self, collection_id: str, entry: SourceCollectionEntry) -> SourceCollection:
        existing = await self.get(collection_id)
        if existing is None:
            raise SourceCollectionNotFoundError(collection_id)
        self._add_entry(collection_id, entry)
        await self._session.flush()
        result = await self.get(collection_id)
        if result is None:
            raise SourceCollectionNotFoundError(collection_id)
        return result

    async def get(self, collection_id: str) -> SourceCollection | None:
        collection_record = await self._session.get(SourceCollectionRecord, collection_id)
        if collection_record is None:
            return None
        entries_statement = select(SourceCollectionEntryRecord).where(
            SourceCollectionEntryRecord.collection_id == collection_id,
        )
        entry_records = (await self._session.execute(entries_statement)).scalars().all()
        return SourceCollection(
            collection_id=collection_record.collection_id,
            scope=collection_record.scope,  # type: ignore[arg-type]
            owner_id=collection_record.owner_id,
            entries=[
                SourceCollectionEntry(
                    entry_id=e.entry_id,
                    title=e.title,
                    authority=e.authority,  # type: ignore[arg-type]
                    url=e.url,
                    excerpt=e.excerpt,
                    subject_key=e.subject_key,
                    claim_value=e.claim_value,
                    copyright_ack=e.copyright_ack,
                )
                for e in entry_records
            ],
        )

    def _add_entry(self, collection_id: str, entry: SourceCollectionEntry) -> None:
        self._session.add(SourceCollectionEntryRecord(
            entry_id=entry.entry_id,
            collection_id=collection_id,
            title=entry.title,
            authority=entry.authority,
            url=entry.url,
            excerpt=entry.excerpt,
            subject_key=entry.subject_key,
            claim_value=entry.claim_value,
            copyright_ack=entry.copyright_ack,
        ))
