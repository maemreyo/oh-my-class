from __future__ import annotations

from typing import Any

type JsonObject = dict[str, Any]


def _artifact_id(artifact: JsonObject) -> str:
    return str(artifact.get("artifact_id") or artifact.get("id") or "")


def _artifact_sort_key(artifact: JsonObject) -> tuple[str, str]:
    return (str(artifact.get("artifact_type", "")), _artifact_id(artifact))


def stable_merge_artifacts(
    prev: list[JsonObject],
    new: list[JsonObject],
) -> list[JsonObject]:
    """Accumulate artifacts by artifact_id; sort by (type, id) for determinism.

    Each parallel Send branch writes its own artifact(s). This reducer accumulates
    all branches' outputs into a stable, id-keyed list regardless of branch
    completion order. New items overwrite prev items with the same artifact_id.
    """
    by_id: dict[str, JsonObject] = {_artifact_id(a): a for a in (prev or [])}
    for artifact in new or []:
        by_id[_artifact_id(artifact)] = artifact
    return sorted(by_id.values(), key=_artifact_sort_key)


def stable_merge_files(prev: list[str], new: list[str]) -> list[str]:
    """Accumulate exported file paths; deduplicate and sort deterministically."""
    seen: set[str] = set(prev or [])
    merged = list(prev or [])
    for path in new or []:
        if path not in seen:
            seen.add(path)
            merged.append(path)
    return sorted(merged)
