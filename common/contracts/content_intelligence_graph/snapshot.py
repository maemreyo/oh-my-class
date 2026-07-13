"""#465 (Content Intelligence Graph): deterministic (hash-based) snapshot
versioning, and the node-id uniqueness check shared by every graph in this
package.

Every `*Graph` in this package already carries a `snapshot_version: str`
field (and is frozen, so a version never mutates in place -- #465's "updating
a graph version does not mutate historical ArtifactDocument provenance").
What was missing is *how* that string gets produced: `compute_snapshot_version`
derives it deterministically from the graph's own content, so two snapshots
built from identical node data always get the identical version string, and
any content change changes it -- a real, checkable hash, not an
arbitrary/manually-bumped label.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Sequence
from typing import Any

from pydantic import BaseModel


class DuplicateNodeIdError(ValueError):
    """A graph snapshot declared the same node id more than once."""

    def __init__(self, duplicate_ids: tuple[str, ...]) -> None:
        self.duplicate_ids = duplicate_ids
        super().__init__(f"duplicate node id(s) in graph snapshot: {', '.join(duplicate_ids)}")


def assert_unique_node_ids(ids: Iterable[str]) -> None:
    """Fail closed on a graph snapshot that declares the same node id twice.

    Raises `DuplicateNodeIdError` naming every id that repeats (not just the
    first), so a caller sees the whole defect in one error.
    """
    seen: set[str] = set()
    duplicates: set[str] = set()
    for node_id in ids:
        if node_id in seen:
            duplicates.add(node_id)
        seen.add(node_id)
    if duplicates:
        raise DuplicateNodeIdError(tuple(sorted(duplicates)))


def compute_snapshot_version(nodes: Sequence[BaseModel], *, prefix: str) -> str:
    """Derive a deterministic `snapshot_version` string from node content.

    Canonicalizes each node via `model_dump(mode="json")` (stable across
    field-order changes in code, since dict keys sort in `json.dumps`), hashes
    the sorted-by-node-json list with sha256, and returns
    `f"{prefix}-{digest[:16]}"`. Same node content (any order) -> same
    version; any content change -> a different version. Truncated to 16 hex
    chars (64 bits) -- collision risk is irrelevant here since this labels a
    snapshot for provenance display/pinning, not a security boundary.
    """
    canonical: list[str] = sorted(
        json.dumps(_to_jsonable(node), sort_keys=True, separators=(",", ":"))
        for node in nodes
    )
    digest = hashlib.sha256("\n".join(canonical).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:16]}"


def _to_jsonable(node: BaseModel) -> Any:
    return node.model_dump(mode="json")
