from __future__ import annotations

import pytest

from common.contracts.objective_decomposition_graph import (
    ObjectiveAccessDeniedError,
    ObjectiveDecompositionGraph,
    ObjectiveMissingError,
    ObjectiveNode,
    decompose_objective,
)


def _node(
    objective_id: str,
    knowledge_component_ids: tuple[str, ...] = ("kc-1",),
    access_scope: str = "system",
    owner_id: str | None = None,
) -> ObjectiveNode:
    return ObjectiveNode(
        objective_id=objective_id,
        description=objective_id,
        knowledge_component_ids=knowledge_component_ids,
        access_scope=access_scope,
        owner_id=owner_id,
    )


def test_decomposition_returns_declared_order_deterministically() -> None:
    graph = ObjectiveDecompositionGraph(snapshot_version="v1", nodes=(
        _node("add-fractions", knowledge_component_ids=("unit-fractions", "common-denominator", "sum-numerators")),
    ))

    result = decompose_objective(graph, "add-fractions")

    assert result == ("unit-fractions", "common-denominator", "sum-numerators")
    assert decompose_objective(graph, "add-fractions") == result


def test_missing_objective_fails_closed() -> None:
    graph = ObjectiveDecompositionGraph(snapshot_version="v1", nodes=(_node("m1"),))

    with pytest.raises(ObjectiveMissingError):
        decompose_objective(graph, "no-such-objective")


def test_denies_access_to_an_objective_outside_visible_scopes() -> None:
    graph = ObjectiveDecompositionGraph(snapshot_version="v1", nodes=(
        _node("m1", access_scope="organization"),
    ))

    with pytest.raises(ObjectiveAccessDeniedError):
        decompose_objective(graph, "m1", visible_access_scopes=frozenset({"system"}))


def test_organization_scope_is_allowed_when_visible() -> None:
    graph = ObjectiveDecompositionGraph(snapshot_version="v1", nodes=(
        _node("m1", access_scope="organization"),
    ))

    result = decompose_objective(graph, "m1", visible_access_scopes=frozenset({"organization"}))

    assert result == ("kc-1",)


def test_private_teacher_objective_denied_to_a_different_teacher() -> None:
    graph = ObjectiveDecompositionGraph(snapshot_version="v1", nodes=(
        _node("m1", access_scope="private_teacher", owner_id="teacher-a"),
    ))

    with pytest.raises(ObjectiveAccessDeniedError):
        decompose_objective(
            graph, "m1",
            visible_access_scopes=frozenset({"private_teacher"}),
            requester_id="teacher-b",
        )


def test_private_teacher_objective_allowed_to_its_own_owner() -> None:
    graph = ObjectiveDecompositionGraph(snapshot_version="v1", nodes=(
        _node("m1", access_scope="private_teacher", owner_id="teacher-a"),
    ))

    result = decompose_objective(
        graph, "m1",
        visible_access_scopes=frozenset({"private_teacher"}),
        requester_id="teacher-a",
    )

    assert result == ("kc-1",)


def test_graph_and_nodes_are_immutable() -> None:
    graph = ObjectiveDecompositionGraph(snapshot_version="v1", nodes=(_node("m1"),))

    with pytest.raises(Exception):  # noqa: B017, PT011 -- pydantic frozen-model error
        graph.nodes[0].objective_id = "changed"  # type: ignore[misc]
