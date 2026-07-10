"""Immutable, checksummed, licensed Media Asset versions (ADR-056).

V2 of the media library: the existing `MediaAssetModel`/`MediaAssetStore`
(SDX-02) mutate `alt_text` in place and have no checksum, license, or
version lineage. Rather than break that shipped, tested V1 flow, this adds
an additive versioned layer -- the same expand-first pattern #426/#427 used
for `ArtifactDocument` V2 alongside the legacy `ArtifactSnapshot`.
"""

from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MediaAssetOwnerScope = Literal["private_teacher", "organization", "system"]

_REMOTE_SCHEMES = ("http://", "https://")


class RemoteSourceRejectedError(ValueError):
    """Raised when a media source is a remote URL where only local/offline
    references are allowed (ADR-056's offline invariant)."""

    def __init__(self, source: str) -> None:
        self.source = source
        super().__init__(f"remote source not allowed: {source!r}")


def is_remote_source(source: str) -> bool:
    return source.startswith(_REMOTE_SCHEMES)


def reject_remote_source(source: str) -> None:
    """Shared guard: raise if `source` is a remote URL.

    The single source of truth for "no remote images/fonts/scripts in a
    production artifact or export" -- `SlideDeckMedia` and this module's own
    version-creation path both call this instead of re-implementing the
    `http(s)://` check independently.
    """
    if is_remote_source(source):
        raise RemoteSourceRejectedError(source)


def compute_checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class MediaAssetVersion(BaseModel):
    """One immutable version of a media asset. `asset_id` is the stable family
    identity across versions; `version_id` identifies this specific version."""

    model_config = ConfigDict(frozen=True)

    version_id: str = Field(min_length=1, max_length=80)
    asset_id: str = Field(min_length=1, max_length=80)
    version: int = Field(ge=1)
    owner_scope: MediaAssetOwnerScope
    owner_id: str = Field(min_length=1, max_length=64)
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    storage_key: str = Field(min_length=1, max_length=255)
    checksum_sha256: str = Field(min_length=64, max_length=64)
    license_note: str | None = Field(default=None, max_length=500)
    alt_text: str | None = Field(default=None, max_length=500)
    parent_version_id: str | None = Field(default=None, min_length=1, max_length=80)


def has_accessible_alt_text(version: MediaAssetVersion) -> bool:
    return version.alt_text is not None and version.alt_text.strip() != ""
