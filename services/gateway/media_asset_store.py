"""Teacher-scoped media asset library store (SDX-02).

Every query is scoped by ``teacher_id`` — the same "only ever touch your own
rows" ownership pattern ``ClassProfileStore`` uses for other teacher-level
(non-run) resources. A lookup for another teacher's ``asset_id`` simply
returns no rows: the same fail-closed shape ``check_run_owner`` gives
run-scoped resources, without needing a separate ``check_teacher_owner``
helper — there is no cross-teacher row to authorize access to in the first
place.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from services.gateway.models import MediaAssetModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class MediaAssetStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_asset(
        self,
        *,
        asset_id: str,
        teacher_id: str,
        filename: str,
        content_type: str,
        storage_key: str,
        tags: list[str],
        alt_text: str | None = None,
    ) -> MediaAssetModel:
        row = MediaAssetModel(
            asset_id=asset_id,
            teacher_id=teacher_id,
            filename=filename,
            content_type=content_type,
            storage_key=storage_key,
            tags=tags,
            alt_text=alt_text,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_asset(self, asset_id: str, teacher_id: str) -> MediaAssetModel | None:
        """Scoped by teacher_id — never returns another teacher's asset."""
        statement = select(MediaAssetModel).where(
            MediaAssetModel.asset_id == asset_id,
            MediaAssetModel.teacher_id == teacher_id,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_assets(
        self,
        teacher_id: str,
        *,
        q: str | None = None,
        tag: str | None = None,
    ) -> list[MediaAssetModel]:
        """List the calling teacher's own assets, optionally filtered.

        # ponytail: filename/tag filtering happens in Python after a
        # teacher-scoped fetch, not in SQL — a `tags` JSON column has no
        # portable "contains element" query, and a teacher's own library is
        # small. Move to JSONB + a GIN index / ILIKE if a library grows large
        # enough for this to matter.
        """
        statement = select(MediaAssetModel).where(MediaAssetModel.teacher_id == teacher_id)
        result = await self._session.execute(statement)
        rows = list(result.scalars().all())
        if q:
            needle = q.strip().lower()
            rows = [row for row in rows if needle in row.filename.lower()]
        if tag:
            rows = [row for row in rows if tag in row.tags]
        rows.sort(key=lambda row: row.created_at, reverse=True)
        return rows

    async def set_alt_text(
        self, asset_id: str, teacher_id: str, alt_text: str,
    ) -> MediaAssetModel | None:
        """SDX-04 integration point: fills in AI-generated alt text once that
        feature exists. Scoped by teacher_id like every other method here."""
        row = await self.get_asset(asset_id, teacher_id)
        if row is None:
            return None
        row.alt_text = alt_text
        await self._session.flush()
        return row
