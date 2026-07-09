"""Object storage for teacher-owned media assets (SDX-02).

Storage keys are flat and teacher-scoped: ``teacher-media/{teacher_id}/{asset_id}{ext}``
— never run-scoped — so a future ``trust-lifecycle/003`` general content
library can absorb these keys unchanged.

# ponytail: stores to local disk, not S3/GCS — no object-storage client
# exists anywhere in this repo yet, and adding one is out of scope for a
# "minimal" library. Swap MediaStorage.save/read for an S3 client behind the
# same two-method signature when one is introduced; the key scheme is
# already S3-key-shaped so that swap is additive, not a rewrite.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_SAFE_EXT_RE = re.compile(r"^[a-z0-9]{1,10}$")
_DEFAULT_EXT = "bin"


def sanitize_extension(filename: str) -> str:
    """Extract a filesystem-safe extension from an uploaded filename.

    Falls back to a fixed placeholder for missing/unusual extensions rather
    than propagating untrusted characters (e.g. ``../``) into a storage key.
    """
    suffix = Path(filename).suffix.removeprefix(".").lower()
    return suffix if _SAFE_EXT_RE.match(suffix) else _DEFAULT_EXT


def build_storage_key(teacher_id: str, asset_id: str, ext: str) -> str:
    """Flat, teacher-scoped storage key — see module docstring."""
    return f"teacher-media/{teacher_id}/{asset_id}.{ext}"


class MediaStorage:
    """Local-disk-backed object storage, keyed by the flat scheme above."""

    def __init__(self, root: str | Path | None = None) -> None:
        self._root = Path(root or os.getenv("MEDIA_STORAGE_ROOT", "data/media-assets"))

    def save(self, storage_key: str, content: bytes) -> None:
        path = self._root / storage_key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def read(self, storage_key: str) -> bytes:
        return (self._root / storage_key).read_bytes()
