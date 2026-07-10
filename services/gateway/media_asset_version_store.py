"""Persistence for immutable Media Asset versions and their artifact dependents."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import select

from common.contracts.media_asset import MediaAssetVersion, compute_checksum
from services.gateway.media_asset_version_models import (
    MediaAssetDependencyRecord,
    MediaAssetVersionRecord,
)
from services.gateway.models import utc_now

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class MediaAssetNotFoundError(LookupError):
    def __init__(self, asset_id: str) -> None:
        self.asset_id = asset_id
        super().__init__(asset_id)


class MediaAssetHasDependentsError(RuntimeError):
    """Raised instead of deleting a media asset that artifact documents still reference."""

    def __init__(self, asset_id: str, dependent_document_ids: list[str]) -> None:
        self.asset_id = asset_id
        self.dependent_document_ids = dependent_document_ids
        super().__init__(f"{asset_id} has {len(dependent_document_ids)} dependent document(s)")


class ChecksumMismatchError(RuntimeError):
    """Raised when stored bytes no longer match their recorded checksum -- the
    offline-packaging integrity guarantee (ADR-056)."""

    def __init__(self, version_id: str) -> None:
        self.version_id = version_id
        super().__init__(f"{version_id}: stored content no longer matches its checksum")


class MediaAssetVersionStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        asset_id: str,
        owner_scope: str,
        owner_id: str,
        filename: str,
        content_type: str,
        storage_key: str,
        content: bytes,
        license_note: str | None = None,
        alt_text: str | None = None,
    ) -> MediaAssetVersion:
        """First version of a new asset family."""
        return await self._insert(
            version_id=f"mediav-{uuid4().hex[:16]}",
            asset_id=asset_id,
            version=1,
            owner_scope=owner_scope,
            owner_id=owner_id,
            filename=filename,
            content_type=content_type,
            storage_key=storage_key,
            content=content,
            license_note=license_note,
            alt_text=alt_text,
            parent_version_id=None,
        )

    async def replace(
        self,
        asset_id: str,
        *,
        filename: str,
        content_type: str,
        storage_key: str,
        content: bytes,
        license_note: str | None = None,
        alt_text: str | None = None,
    ) -> tuple[MediaAssetVersion, list[str]]:
        """Create the next version, preserving `owner_scope`/`owner_id` from the head.

        Returns the new version plus the artifact document ids that
        depended on the *previous* head -- visible dependency impact, never
        silently propagated onto the new version.
        """
        head = await self.get_latest(asset_id)
        if head is None:
            raise MediaAssetNotFoundError(asset_id)
        impacted = await self._dependent_document_ids(head.version_id)
        next_version = await self._insert(
            version_id=f"mediav-{uuid4().hex[:16]}",
            asset_id=asset_id,
            version=head.version + 1,
            owner_scope=head.owner_scope,
            owner_id=head.owner_id,
            filename=filename,
            content_type=content_type,
            storage_key=storage_key,
            content=content,
            license_note=license_note,
            alt_text=alt_text,
            parent_version_id=head.version_id,
        )
        return next_version, impacted

    async def get_latest(self, asset_id: str) -> MediaAssetVersion | None:
        statement = (
            select(MediaAssetVersionRecord)
            .where(
                MediaAssetVersionRecord.asset_id == asset_id,
                MediaAssetVersionRecord.deleted_at.is_(None),
            )
            .order_by(MediaAssetVersionRecord.version.desc())
            .limit(1)
        )
        record = (await self._session.execute(statement)).scalar_one_or_none()
        return _to_contract(record) if record is not None else None

    async def list_versions(self, asset_id: str) -> list[MediaAssetVersion]:
        statement = (
            select(MediaAssetVersionRecord)
            .where(MediaAssetVersionRecord.asset_id == asset_id)
            .order_by(MediaAssetVersionRecord.version.desc())
        )
        records = (await self._session.execute(statement)).scalars().all()
        return [_to_contract(r) for r in records]

    async def record_dependency(self, media_version_id: str, document_id: str) -> None:
        self._session.add(MediaAssetDependencyRecord(
            media_version_id=media_version_id, document_id=document_id,
        ))
        await self._session.flush()

    async def soft_delete(self, asset_id: str) -> None:
        """Blocked while any artifact document still depends on the current head."""
        head = await self.get_latest(asset_id)
        if head is None:
            raise MediaAssetNotFoundError(asset_id)
        dependents = await self._dependent_document_ids(head.version_id)
        if dependents:
            raise MediaAssetHasDependentsError(asset_id, dependents)
        record = await self._session.get(MediaAssetVersionRecord, head.version_id)
        if record is not None:
            record.deleted_at = utc_now()
            await self._session.flush()

    async def verify_checksum(self, version_id: str, content: bytes) -> None:
        """Re-hash `content` and compare to the recorded checksum -- the integrity
        check an offline package must pass before bundling these bytes."""
        record = await self._session.get(MediaAssetVersionRecord, version_id)
        if record is None:
            raise MediaAssetNotFoundError(version_id)
        if compute_checksum(content) != record.checksum_sha256:
            raise ChecksumMismatchError(version_id)

    async def _dependent_document_ids(self, media_version_id: str) -> list[str]:
        statement = select(MediaAssetDependencyRecord.document_id).where(
            MediaAssetDependencyRecord.media_version_id == media_version_id,
        )
        return [row[0] for row in (await self._session.execute(statement)).all()]

    async def _insert(
        self,
        *,
        version_id: str,
        asset_id: str,
        version: int,
        owner_scope: str,
        owner_id: str,
        filename: str,
        content_type: str,
        storage_key: str,
        content: bytes,
        license_note: str | None,
        alt_text: str | None,
        parent_version_id: str | None,
    ) -> MediaAssetVersion:
        record = MediaAssetVersionRecord(
            version_id=version_id,
            asset_id=asset_id,
            version=version,
            owner_scope=owner_scope,
            owner_id=owner_id,
            filename=filename,
            content_type=content_type,
            storage_key=storage_key,
            checksum_sha256=compute_checksum(content),
            license_note=license_note,
            alt_text=alt_text,
            parent_version_id=parent_version_id,
        )
        self._session.add(record)
        await self._session.flush()
        return _to_contract(record)


def _to_contract(record: MediaAssetVersionRecord) -> MediaAssetVersion:
    return MediaAssetVersion(
        version_id=record.version_id,
        asset_id=record.asset_id,
        version=record.version,
        owner_scope=record.owner_scope,  # type: ignore[arg-type]
        owner_id=record.owner_id,
        filename=record.filename,
        content_type=record.content_type,
        storage_key=record.storage_key,
        checksum_sha256=record.checksum_sha256,
        license_note=record.license_note,
        alt_text=record.alt_text,
        parent_version_id=record.parent_version_id,
    )
