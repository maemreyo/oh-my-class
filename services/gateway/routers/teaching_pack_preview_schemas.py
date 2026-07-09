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


class SlideDeckBlockEditResponse(BaseModel):
    run_id: str
    artifact_id: str
    block_id: str
    base_snapshot_id: str
    snapshot_id: str
