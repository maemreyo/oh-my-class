from __future__ import annotations

from datetime import datetime  # noqa: TC003 - Pydantic resolves the response field at runtime
from typing import Literal

from pydantic import BaseModel, Field


class RenderedSnapshotMetadataResponse(BaseModel):
    snapshot_id: str
    artifact_id: str
    artifact_type: str
    content_hash: str
    html_hash: str
    renderer_version: str
    template_version: str
    theme_version: str
    standalone_valid: bool
    approved_at: datetime | None


class SnapshotApprovalRequest(BaseModel):
    snapshot_ids: list[str] = Field(min_length=1)


class SnapshotApprovalResponse(BaseModel):
    run_id: str
    approved_snapshot_ids: list[str]


class TranslateSlideDeckRequest(BaseModel):
    """SDX-01: "Dịch deck này" -- EN<->VI only, no generic language selector."""

    target_language: Literal["en", "vi"]


class TranslateSlideDeckResponse(BaseModel):
    run_id: str
    source_snapshot_id: str
    snapshot_id: str
    deck_id: str


class SlideDeckBlockEditRequest(BaseModel):
    """SDE-04: optimistic-locked scoped block edit against a slide deck snapshot."""

    base_snapshot_id: str = Field(min_length=1)
    new_content: str = Field(min_length=1, max_length=2000)
    rationale: str = ""
    # SDE-08: distinguishes a teacher-applied AI rewrite from a manual edit in
    # the resulting `content_version.created` event. Restricted to the two
    # known authorities (a `Literal`, not a free string) -- this is a trust
    # boundary the client controls, so an unrecognized value is a 422, not a
    # silently-accepted new authority tag.
    authority: Literal["teacher_edit", "ai_assisted_edit"] = "teacher_edit"


class SlideDeckBlockEditResponse(BaseModel):
    run_id: str
    artifact_id: str
    block_id: str
    base_snapshot_id: str
    snapshot_id: str


class SlideDeckBlockRewriteSuggestionRequest(BaseModel):
    """SDE-08: request a rewrite CANDIDATE for one block -- never persists.

    Exactly one of `preset`/`instruction` is expected (the frontend UI only
    ever sends one); both route through the identical
    `resolve_rewrite_instruction` function server-side, so there is no
    separate/less-validated freeform path (AC1).
    """

    preset: str | None = None
    instruction: str | None = Field(default=None, max_length=500)


class SlideDeckBlockRewriteSuggestionResponse(BaseModel):
    block_id: str
    before: str
    after: str


class ArtifactVersionSummary(BaseModel):
    """SDE-05: one row in the linear, newest-first version-history list."""

    snapshot_id: str
    created_at: datetime
    authority: str
    label: str
    is_current: bool


class ArtifactVersionListResponse(BaseModel):
    run_id: str
    artifact_id: str
    total: int
    limit: int
    offset: int
    versions: list[ArtifactVersionSummary]


class RestoreArtifactVersionRequest(BaseModel):
    """SDE-05: optimistic-locked restore, same shape as the block-edit request."""

    base_snapshot_id: str = Field(min_length=1)


class RestoreArtifactVersionResponse(BaseModel):
    run_id: str
    artifact_id: str
    restored_from_snapshot_id: str
    base_snapshot_id: str
    snapshot_id: str
