from __future__ import annotations

import pytest

from common.contracts.prerequisite_graph import (
    PrerequisiteCycleError,
    PrerequisiteGraph,
    PrerequisiteMissingNodeError,
    PrerequisiteNode,
    PrerequisiteScopeConflictError,
    prerequisite_closure,
)


def _node(node_id: str, requires: tuple[str, ...] = (), scope: str = "math.grade_5") -> PrerequisiteNode:
    return PrerequisiteNode(node_id=node_id, description=node_id, scope=scope, requires=requires)


def test_prerequisite_closure_is_deterministic_and_deepest_first() -> None:
    graph = PrerequisiteGraph(snapshot_version="v1", nodes=(
        _node("equivalent-fractions", requires=("compare-fractions",)),
        _node("compare-fractions", requires=("unit-fractions",)),
        _node("unit-fractions"),
    ))

    closure = prerequisite_closure(graph, "equivalent-fractions")

    assert closure == ("unit-fractions", "compare-fractions")
    # Re-running against the same immutable snapshot is byte-identical.
    assert prerequisite_closure(graph, "equivalent-fractions") == closure


def test_prerequisite_closure_merges_diamond_dependencies_without_duplication() -> None:
    graph = PrerequisiteGraph(snapshot_version="v1", nodes=(
        _node("add-fractions", requires=("common-denominator", "unit-fractions")),
        _node("common-denominator", requires=("unit-fractions",)),
        _node("unit-fractions"),
    ))

    closure = prerequisite_closure(graph, "add-fractions")

    assert closure == ("unit-fractions", "common-denominator")


def test_prerequisite_closure_detects_a_cycle() -> None:
    graph = PrerequisiteGraph(snapshot_version="v1", nodes=(
        _node("a", requires=("b",)),
        _node("b", requires=("c",)),
        _node("c", requires=("a",)),
    ))

    with pytest.raises(PrerequisiteCycleError) as excinfo:
        prerequisite_closure(graph, "a")
    assert excinfo.value.cycle == ("a", "b", "c")


def test_prerequisite_closure_detects_a_missing_node() -> None:
    graph = PrerequisiteGraph(snapshot_version="v1", nodes=(
        _node("equivalent-fractions", requires=("nonexistent-node",)),
    ))

    with pytest.raises(PrerequisiteMissingNodeError) as excinfo:
        prerequisite_closure(graph, "equivalent-fractions")
    assert excinfo.value.missing_requirement_id == "nonexistent-node"


def test_prerequisite_closure_rejects_target_not_in_graph() -> None:
    graph = PrerequisiteGraph(snapshot_version="v1", nodes=(_node("unit-fractions"),))

    with pytest.raises(PrerequisiteMissingNodeError):
        prerequisite_closure(graph, "does-not-exist")


def test_prerequisite_closure_detects_a_cross_scope_conflict() -> None:
    graph = PrerequisiteGraph(snapshot_version="v1", nodes=(
        _node("equivalent-fractions", requires=("photosynthesis",), scope="math.grade_5"),
        _node("photosynthesis", scope="science.grade_5"),
    ))

    with pytest.raises(PrerequisiteScopeConflictError) as excinfo:
        prerequisite_closure(graph, "equivalent-fractions")
    assert excinfo.value.node_id == "photosynthesis"
    assert excinfo.value.expected_scope == "math.grade_5"
    assert excinfo.value.actual_scope == "science.grade_5"


def test_prerequisite_graph_snapshot_is_immutable() -> None:
    graph = PrerequisiteGraph(snapshot_version="v1", nodes=(_node("unit-fractions"),))

    with pytest.raises(Exception, match="frozen|immutable"):
        graph.snapshot_version = "v2"  # type: ignore[misc]


def test_prerequisite_graph_requires_at_least_one_node() -> None:
    with pytest.raises(Exception, match="at least 1 item|too_short"):
        PrerequisiteGraph(snapshot_version="v1", nodes=())
