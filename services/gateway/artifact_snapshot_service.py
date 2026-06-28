"""Production service for rendering artifacts and persisting snapshots.

This service bridges the renderer adapter and snapshot store, providing a clean
interface for producing artifact snapshots in production pipelines.

The flow:
  1. Accept ArtifactContent (dict with title, sections, theme, etc.)
  2. Render to standalone HTML via renderer_adapter.render_artifact_content()
  3. Strip student answer keys via snapshot_store helpers
  4. Persist via TeachingPackSnapshotStore.create_snapshot()
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from services.gateway.teaching_pack_snapshot_store import (
    ArtifactSnapshotCreate,
    TeachingPackSnapshotStore,
)
from services.gateway.renderer_adapter import render_artifact_content, RendererConfig
from services.gateway.teaching_pack_types import RunId

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def produce_artifact_snapshot(
    session: AsyncSession,
    *,
    run_id: RunId,
    artifact_content: dict,
    artifact_id: str | None = None,
    artifact_type: str = "lesson",
    renderer_version: str = "1.0",
    template_version: str = "unknown",
    theme_version: str = "unknown",
    renderer_config: RendererConfig | None = None,
) -> str:
    """Render and persist an artifact snapshot.

    Takes artifact content, renders it to standalone HTML via the TypeScript renderer,
    strips student answer keys, and persists the snapshot to the database.

    Args:
        session: Database session for persistence.
        run_id: The run this artifact belongs to.
        artifact_content: Artifact content dict (title, sections, theme, etc.).
        artifact_id: Optional artifact ID; generated if not provided.
        artifact_type: Type of artifact (lesson, worksheet, quiz, etc.).
        renderer_version: Version of the renderer used.
        template_version: Version of the template used.
        theme_version: Version of the theme used.
        renderer_config: Optional renderer subprocess configuration.

    Returns:
        The snapshot_id of the persisted snapshot.

    Raises:
        RendererAdapterError: If rendering fails.
        SnapshotPersistenceError: If snapshot cannot be persisted.
    """
    if artifact_id is None:
        artifact_id = f"artifact-{uuid4().hex[:8]}"

    # Step 1: Render to standalone HTML
    rendered_html = await render_artifact_content(
        artifact_content,
        config=renderer_config,
    )

    # Step 2: Persist via snapshot store
    # The snapshot store handles stripping answer keys internally
    snapshot_id = f"snapshot-{uuid4().hex[:12]}"
    snapshot_store = TeachingPackSnapshotStore(session)
    snapshot_create = ArtifactSnapshotCreate(
        snapshot_id=snapshot_id,
        run_id=run_id,
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        content_json=artifact_content,
        rendered_html=rendered_html,
        renderer_version=renderer_version,
        template_version=template_version,
        theme_version=theme_version,
        student_rendered_html=None,  # Let snapshot store derive from content_json
        version_mismatch_policy="warn",
    )

    snapshot_result = await snapshot_store.create_snapshot(snapshot_create)
    return snapshot_result.snapshot_id
