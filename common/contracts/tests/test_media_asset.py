from __future__ import annotations

import pytest

from common.contracts.media_asset import (
    MediaAssetVersion,
    RemoteSourceRejectedError,
    compute_checksum,
    has_accessible_alt_text,
    is_remote_source,
    reject_remote_source,
)


def test_remote_http_and_https_sources_are_detected() -> None:
    assert is_remote_source("http://example.com/a.png") is True
    assert is_remote_source("https://example.com/a.png") is True
    assert is_remote_source("teacher-media/teacher-1/media-1.png") is False
    assert is_remote_source("data:image/png;base64,abc") is False


def test_reject_remote_source_raises_only_for_remote() -> None:
    with pytest.raises(RemoteSourceRejectedError):
        reject_remote_source("https://example.com/a.png")
    reject_remote_source("teacher-media/teacher-1/media-1.png")  # must not raise


def test_checksum_is_deterministic_and_content_sensitive() -> None:
    assert compute_checksum(b"hello") == compute_checksum(b"hello")
    assert compute_checksum(b"hello") != compute_checksum(b"hello!")
    assert len(compute_checksum(b"hello")) == 64


def _version(**overrides: object) -> MediaAssetVersion:
    defaults: dict[str, object] = {
        "version_id": "mediav-1",
        "asset_id": "media-1",
        "version": 1,
        "owner_scope": "private_teacher",
        "owner_id": "teacher-1",
        "filename": "diagram.png",
        "content_type": "image/png",
        "storage_key": "teacher-media/teacher-1/media-1.png",
        "checksum_sha256": "a" * 64,
    }
    defaults.update(overrides)
    return MediaAssetVersion(**defaults)


def test_blank_alt_text_is_not_accessible() -> None:
    assert has_accessible_alt_text(_version(alt_text=None)) is False
    assert has_accessible_alt_text(_version(alt_text="  ")) is False
    assert has_accessible_alt_text(_version(alt_text="A labeled diagram of a plant cell.")) is True
