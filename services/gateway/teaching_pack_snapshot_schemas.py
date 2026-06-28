"""Data schemas for artifact snapshot operations.

Frozen dataclasses for snapshot creation and retrieval (separate from ORM models).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from datetime import datetime

    from services.gateway.teaching_pack_types import JsonObject

from services.gateway.teaching_pack_types import (
    RunId,  # noqa: TC001 — used in dataclass field types at runtime
)


@dataclass(frozen=True, slots=True)
class ArtifactSnapshotCreate:
    """Input contract for snapshot creation.
    
    Immutable payload passed to TeachingPackSnapshotStore.create_snapshot().
    """

    snapshot_id: str
    run_id: RunId
    artifact_id: str
    artifact_type: str
    content_json: JsonObject
    rendered_html: str
    renderer_version: str
    template_version: str = "unknown"
    theme_version: str = "unknown"
    student_rendered_html: str | None = None
    version_mismatch_policy: Literal["block", "warn"] = "block"


@dataclass(frozen=True, slots=True)
class ArtifactSnapshotRead:
    """Output contract for snapshot retrieval.

    Immutable snapshot state returned from store queries.
    """

    snapshot_id: str
    run_id: RunId
    artifact_id: str
    artifact_type: str
    content_hash: str
    html_hash: str
    content_json: JsonObject | None
    rendered_html: str
    student_rendered_html: str
    renderer_version: str
    template_version: str
    theme_version: str
    standalone_valid: bool
    approved_at: datetime | None
