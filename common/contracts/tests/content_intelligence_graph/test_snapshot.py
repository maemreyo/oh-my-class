from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.content_intelligence_graph.prerequisite import PrerequisiteGraph, PrerequisiteNode
from common.contracts.content_intelligence_graph.snapshot import (
    DuplicateNodeIdError,
    assert_unique_node_ids,
    compute_snapshot_version,
)


def _node(node_id: str) -> PrerequisiteNode:
    return PrerequisiteNode(node_id=node_id, description="d", scope="s")


def test_assert_unique_node_ids_passes_for_distinct_ids() -> None:
    assert_unique_node_ids(["a", "b", "c"])  # no raise


def test_assert_unique_node_ids_raises_naming_all_duplicates() -> None:
    with pytest.raises(DuplicateNodeIdError) as exc:
        assert_unique_node_ids(["a", "b", "a", "c", "b"])
    assert exc.value.duplicate_ids == ("a", "b")


def test_compute_snapshot_version_is_deterministic_for_same_content() -> None:
    nodes = (_node("a"), _node("b"))
    v1 = compute_snapshot_version(nodes, prefix="p")
    v2 = compute_snapshot_version(nodes, prefix="p")
    assert v1 == v2


def test_compute_snapshot_version_ignores_declaration_order() -> None:
    forward = compute_snapshot_version((_node("a"), _node("b")), prefix="p")
    reverse = compute_snapshot_version((_node("b"), _node("a")), prefix="p")
    assert forward == reverse


def test_compute_snapshot_version_changes_with_content() -> None:
    v1 = compute_snapshot_version((_node("a"),), prefix="p")
    v2 = compute_snapshot_version((_node("a-changed"),), prefix="p")
    assert v1 != v2


def test_compute_snapshot_version_uses_prefix() -> None:
    v1 = compute_snapshot_version((_node("a"),), prefix="p1")
    v2 = compute_snapshot_version((_node("a"),), prefix="p2")
    assert v1 != v2
    assert v1.startswith("p1-")
    assert v2.startswith("p2-")


def test_graph_rejects_duplicate_node_ids() -> None:
    with pytest.raises(ValidationError, match="duplicate node id"):
        PrerequisiteGraph(
            snapshot_version="v1",
            nodes=(_node("dup"), _node("dup")),
        )


def test_graph_snapshot_version_is_immutable_field() -> None:
    graph = PrerequisiteGraph(snapshot_version="v1", nodes=(_node("a"),))
    with pytest.raises(Exception):  # noqa: B017, PT011 -- pydantic frozen-model error
        graph.snapshot_version = "v2"  # type: ignore[misc]
