"""Snapshot storage and persistence for artifact rendering.

Main store class and snapshot hashing utilities.
Imports are re-exported for backward compatibility with existing callers.
"""

from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from services.gateway.pipeline_v2_snapshot_errors import (
    AnswerKeyLeakageError,
    NonStandaloneSnapshotApprovalError,
    SnapshotPersistenceError,
    SnapshotVersionMismatchError,
)
from services.gateway.pipeline_v2_snapshot_html import (
    is_standalone_html,
    render_student_preview_html,
)
from services.gateway.pipeline_v2_snapshot_models import ArtifactSnapshot
from services.gateway.pipeline_v2_snapshot_schemas import (
    ArtifactSnapshotCreate,
    ArtifactSnapshotRead,
)
from services.gateway.pipeline_v2_snapshot_validators import (
    _validate_snapshot_versions,
    remove_answer_keys_from_html,
    validate_answer_key_isolation,
)
from services.gateway.pipeline_v2_types import RunId

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from services.gateway.pipeline_v2_types import JsonObject

# Re-export for backward compatibility
__all__ = [
    "PipelineV2SnapshotStore",
    "ArtifactSnapshotCreate",
    "ArtifactSnapshotRead",
    "AnswerKeyLeakageError",
    "SnapshotPersistenceError",
    "NonStandaloneSnapshotApprovalError",
    "SnapshotVersionMismatchError",
    "snapshot_content_hash",
    "render_student_preview_html",
    "remove_answer_keys_from_html",
    "validate_answer_key_isolation",
    "is_standalone_html",
]


class PipelineV2SnapshotStore:
    """Manages persistence and retrieval of artifact snapshots.

    Enforces answer-key isolation (INVARIANT-05) and standalone HTML validation.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def has_snapshot(self, content_hash: str) -> bool:
        statement = select(ArtifactSnapshot.snapshot_id).where(
            ArtifactSnapshot.content_hash == content_hash,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def create_snapshot(self, payload: ArtifactSnapshotCreate) -> ArtifactSnapshotRead:
        student_html = payload.student_rendered_html or render_student_preview_html(
            payload.content_json,
        )
        student_html_safe = remove_answer_keys_from_html(student_html)

        isolation_issues = validate_answer_key_isolation(payload.rendered_html)
        if isolation_issues:
            raise AnswerKeyLeakageError(payload.snapshot_id, isolation_issues)

        content_hash = snapshot_content_hash(payload.content_json, payload.rendered_html)
        html_hash = sha256(payload.rendered_html.encode()).hexdigest()
        standalone_valid = is_standalone_html(payload.rendered_html)
        statement = pg_insert(ArtifactSnapshot).values(
            snapshot_id=payload.snapshot_id,
            run_id=payload.run_id,
            artifact_id=payload.artifact_id,
            artifact_type=payload.artifact_type,
            content_hash=content_hash,
            html_hash=html_hash,
            content_json=payload.content_json,
            rendered_html=payload.rendered_html,
            student_rendered_html=student_html_safe,
            renderer_version=payload.renderer_version,
            template_version=payload.template_version,
            theme_version=payload.theme_version,
            standalone_valid=standalone_valid,
        ).on_conflict_do_nothing(
            index_elements=["content_hash"],
        )
        await self._session.execute(statement)
        existing_snapshot = await self._get_by_content_hash(content_hash)
        if existing_snapshot is not None:
            _validate_snapshot_versions(payload, existing_snapshot)
        snapshot = await self.get_snapshot(payload.run_id, payload.snapshot_id)
        if snapshot is None:
            snapshot = await self.get_by_run_content_hash(payload.run_id, content_hash)
        if snapshot is None:
            raise SnapshotPersistenceError(payload.snapshot_id)
        return snapshot

    async def _get_by_content_hash(self, content_hash: str) -> ArtifactSnapshot | None:
        statement = select(ArtifactSnapshot).where(ArtifactSnapshot.content_hash == content_hash)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_snapshot(self, run_id: RunId, snapshot_id: str) -> ArtifactSnapshotRead | None:
        statement = select(ArtifactSnapshot).where(
            ArtifactSnapshot.run_id == run_id,
            ArtifactSnapshot.snapshot_id == snapshot_id,
        )
        result = await self._session.execute(statement)
        snapshot = result.scalar_one_or_none()
        if snapshot is None:
            return None
        return _read_snapshot(snapshot)

    async def get_by_run_content_hash(
        self,
        run_id: RunId,
        content_hash: str,
    ) -> ArtifactSnapshotRead | None:
        statement = select(ArtifactSnapshot).where(
            ArtifactSnapshot.run_id == run_id,
            ArtifactSnapshot.content_hash == content_hash,
        )
        result = await self._session.execute(statement)
        snapshot = result.scalar_one_or_none()
        if snapshot is None:
            return None
        return _read_snapshot(snapshot)

    async def list_run_snapshots(self, run_id: RunId) -> list[ArtifactSnapshotRead]:
        statement = select(ArtifactSnapshot).where(ArtifactSnapshot.run_id == run_id)
        result = await self._session.execute(statement)
        return [_read_snapshot(snapshot) for snapshot in result.scalars().all()]

    async def approve_snapshots(self, run_id: RunId, snapshot_ids: list[str]) -> int:
        statement = select(ArtifactSnapshot).where(
            ArtifactSnapshot.run_id == run_id,
            ArtifactSnapshot.snapshot_id.in_(snapshot_ids),
        ).with_for_update()
        result = await self._session.execute(statement)
        snapshots = list(result.scalars().all())
        for snapshot in snapshots:
            if not snapshot.standalone_valid:
                raise NonStandaloneSnapshotApprovalError(snapshot.snapshot_id)
            snapshot.approved_at = datetime.now(tz=snapshot.created_at.tzinfo)
        await self._session.flush()
        return len(snapshots)


def snapshot_content_hash(content_json: JsonObject, rendered_html: str) -> str:
    """Hash snapshot content for deduplication.

    Combines canonical JSON and rendered HTML into a single content hash.
    """
    digest = sha256()
    canonical_content = json.dumps(
        content_json,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    digest.update(canonical_content.encode())
    digest.update(b"\0")
    digest.update(rendered_html.encode())
    return digest.hexdigest()


def _read_snapshot(snapshot: ArtifactSnapshot) -> ArtifactSnapshotRead:
    """Convert ORM ArtifactSnapshot to read schema."""
    return ArtifactSnapshotRead(
        snapshot_id=snapshot.snapshot_id,
        run_id=RunId(snapshot.run_id),
        artifact_id=snapshot.artifact_id,
        artifact_type=snapshot.artifact_type,
        content_hash=snapshot.content_hash,
        html_hash=snapshot.html_hash,
        content_json=snapshot.content_json,
        rendered_html=snapshot.rendered_html,
        student_rendered_html=snapshot.student_rendered_html,
        renderer_version=snapshot.renderer_version,
        template_version=snapshot.template_version,
        theme_version=snapshot.theme_version,
        standalone_valid=snapshot.standalone_valid,
        approved_at=snapshot.approved_at,
    )
