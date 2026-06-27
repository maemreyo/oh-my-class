from __future__ import annotations

from datetime import datetime  # noqa: TC003 - Pydantic resolves the response field at runtime

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
