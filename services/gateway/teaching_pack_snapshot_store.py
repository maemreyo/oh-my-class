"""Snapshot storage and persistence for artifact rendering.

Main store class and snapshot hashing utilities.
Imports are re-exported for backward compatibility with existing callers.
"""

from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from typing import TYPE_CHECKING

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from services.gateway.teaching_pack_snapshot_errors import (
    AnswerKeyLeakageError,
    NonStandaloneSnapshotApprovalError,
    SnapshotBaseVersionConflictError,
    SnapshotPersistenceError,
    SnapshotVersionMismatchError,
)
from services.gateway.teaching_pack_snapshot_html import (
    is_standalone_html,
    render_student_preview_html,
)
from services.gateway.teaching_pack_snapshot_models import ArtifactSnapshot
from services.gateway.teaching_pack_snapshot_schemas import (
    ArtifactSnapshotCreate,
    ArtifactSnapshotRead,
)
from services.gateway.teaching_pack_snapshot_validators import (
    _validate_snapshot_versions,
    bake_effective_slide_deck_display_preferences,
    remove_answer_keys_from_html,
    validate_answer_key_isolation,
)
from services.gateway.teaching_pack_types import RunId

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from services.gateway.teaching_pack_types import JsonObject

# Re-export for backward compatibility
__all__ = [
    "TeachingPackSnapshotStore",
    "ArtifactSnapshotCreate",
    "ArtifactSnapshotRead",
    "AnswerKeyLeakageError",
    "SnapshotPersistenceError",
    "NonStandaloneSnapshotApprovalError",
    "SnapshotVersionMismatchError",
    "SnapshotBaseVersionConflictError",
    "snapshot_content_hash",
    "render_student_preview_html",
    "remove_answer_keys_from_html",
    "validate_answer_key_isolation",
    "is_standalone_html",
]


class TeachingPackSnapshotStore:
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
        # ADR-043/SDH-09: bake resolved display preferences into the stored
        # content before hashing/persisting, so export replay reproduces the
        # exact surface/layout/chrome regardless of future default changes.
        content_json = bake_effective_slide_deck_display_preferences(
            payload.artifact_type, payload.content_json,
        )
        student_html = payload.student_rendered_html or payload.rendered_html
        student_html_safe = remove_answer_keys_from_html(student_html)

        isolation_issues = validate_answer_key_isolation(payload.rendered_html)
        if isolation_issues:
            raise AnswerKeyLeakageError(payload.snapshot_id, isolation_issues)

        content_hash = snapshot_content_hash(content_json, payload.rendered_html)
        html_hash = sha256(payload.rendered_html.encode()).hexdigest()
        standalone_valid = is_standalone_html(payload.rendered_html)
        statement = (
            pg_insert(ArtifactSnapshot)
            .values(
                snapshot_id=payload.snapshot_id,
                run_id=payload.run_id,
                artifact_id=payload.artifact_id,
                artifact_type=payload.artifact_type,
                content_hash=content_hash,
                html_hash=html_hash,
                content_json=content_json,
                rendered_html=payload.rendered_html,
                student_rendered_html=student_html_safe,
                renderer_version=payload.renderer_version,
                template_version=payload.template_version,
                theme_version=payload.theme_version,
                standalone_valid=standalone_valid,
            )
            .on_conflict_do_nothing(
                index_elements=["content_hash"],
            )
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

    async def get_latest_snapshot(self, run_id: RunId, artifact_id: str) -> ArtifactSnapshotRead | None:
        """Return the most recently created snapshot for one artifact in a run.

        SDE-04: every edit creates a brand-new row (no in-place mutation, no
        version column), so the "current head" of an artifact's version
        lineage is simply its newest row by `created_at`.
        """
        statement = (
            select(ArtifactSnapshot)
            .where(ArtifactSnapshot.run_id == run_id, ArtifactSnapshot.artifact_id == artifact_id)
            .order_by(ArtifactSnapshot.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(statement)
        snapshot = result.scalar_one_or_none()
        return _read_snapshot(snapshot) if snapshot is not None else None

    async def list_artifact_snapshot_versions(
        self,
        run_id: RunId,
        artifact_id: str,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[ArtifactSnapshotRead], int]:
        """SDE-05: paginated, newest-first version lineage for one artifact.

        Returns `(page, total)` -- `total` is the full lineage length so the
        caller can render "page N of M" / decide whether more pages remain
        without fetching every row.
        """
        count_statement = select(func.count()).select_from(ArtifactSnapshot).where(
            ArtifactSnapshot.run_id == run_id, ArtifactSnapshot.artifact_id == artifact_id,
        )
        total = (await self._session.execute(count_statement)).scalar_one()
        statement = (
            select(ArtifactSnapshot)
            .where(ArtifactSnapshot.run_id == run_id, ArtifactSnapshot.artifact_id == artifact_id)
            .order_by(ArtifactSnapshot.created_at.desc(), ArtifactSnapshot.snapshot_id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(statement)
        page = [_read_snapshot(snapshot) for snapshot in result.scalars().all()]
        return page, total

    async def get_earliest_snapshot_id(self, run_id: RunId, artifact_id: str) -> str | None:
        """The artifact's first-ever snapshot (materialization, not an edit) -- used to
        label that one version "Initial version" instead of "Manual edit"."""
        statement = (
            select(ArtifactSnapshot.snapshot_id)
            .where(ArtifactSnapshot.run_id == run_id, ArtifactSnapshot.artifact_id == artifact_id)
            .order_by(ArtifactSnapshot.created_at.asc(), ArtifactSnapshot.snapshot_id.asc())
            .limit(1)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create_scoped_edit_snapshot(
        self,
        *,
        run_id: RunId,
        artifact_id: str,
        base_snapshot_id: str,
        new_snapshot: ArtifactSnapshotCreate,
    ) -> ArtifactSnapshotRead:
        """Create a new snapshot version iff `base_snapshot_id` is still the head.

        Optimistic locking, no pessimistic row locks: acquires a
        transaction-scoped Postgres advisory lock keyed on `artifact_id`
        (mirrors `TeachingPackRunStore._next_sequence`'s existing pattern for
        the same async read-check-write race) so two concurrent edits against
        the same artifact serialize on this narrow critical section -- the
        first to commit wins; the second re-reads the now-advanced head and
        raises `SnapshotBaseVersionConflictError` instead of overwriting.
        Releases automatically at the caller's commit/rollback.
        """
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:artifact_id))"),
            {"artifact_id": artifact_id},
        )
        head = await self.get_latest_snapshot(run_id, artifact_id)
        current_head_id = head.snapshot_id if head is not None else None
        if current_head_id != base_snapshot_id:
            raise SnapshotBaseVersionConflictError(base_snapshot_id, current_head_id)
        return await self.create_snapshot(new_snapshot)

    async def approve_snapshots(self, run_id: RunId, snapshot_ids: list[str]) -> int:
        statement = (
            select(ArtifactSnapshot)
            .where(
                ArtifactSnapshot.run_id == run_id,
                ArtifactSnapshot.snapshot_id.in_(snapshot_ids),
            )
            .with_for_update()
        )
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
        created_at=snapshot.created_at,
    )
