from __future__ import annotations

import pytest

from common.contracts.content_intelligence_graph.exercise_candidate import (
    ExerciseCandidateAccessDeniedError,
    ExerciseCandidateGraph,
    ExerciseCandidateNode,
    retrieve_exercise_candidates,
)


def _node(
    candidate_id: str,
    knowledge_component_id: str = "fractions.add",
    task_model: str = "multiple_choice",
    misconception_targets: tuple[str, ...] = (),
    access_scope: str = "system",
    owner_id: str | None = None,
) -> ExerciseCandidateNode:
    return ExerciseCandidateNode(
        candidate_id=candidate_id,
        knowledge_component_id=knowledge_component_id,
        task_model=task_model,
        misconception_targets=misconception_targets,
        access_scope=access_scope,
        owner_id=owner_id,
    )


def test_retrieval_is_deterministic_and_sorted_by_id() -> None:
    graph = ExerciseCandidateGraph(snapshot_version="v1", nodes=(
        _node("zed-candidate"),
        _node("alpha-candidate"),
    ))

    result = retrieve_exercise_candidates(graph, "fractions.add")

    assert [node.candidate_id for node in result] == ["alpha-candidate", "zed-candidate"]
    assert retrieve_exercise_candidates(graph, "fractions.add") == result


def test_retrieval_filters_by_knowledge_component() -> None:
    graph = ExerciseCandidateGraph(snapshot_version="v1", nodes=(
        _node("c1", knowledge_component_id="fractions.add"),
        _node("c2", knowledge_component_id="fractions.subtract"),
    ))

    result = retrieve_exercise_candidates(graph, "fractions.subtract")

    assert [node.candidate_id for node in result] == ["c2"]


def test_unknown_knowledge_component_returns_empty_not_an_error() -> None:
    graph = ExerciseCandidateGraph(snapshot_version="v1", nodes=(_node("c1"),))

    result = retrieve_exercise_candidates(graph, "no-such-component")

    assert result == ()


def test_filters_by_target_misconception() -> None:
    graph = ExerciseCandidateGraph(snapshot_version="v1", nodes=(
        _node("c1", misconception_targets=("m1",)),
        _node("c2", misconception_targets=("m2",)),
        _node("c3", misconception_targets=("m1", "m2")),
    ))

    result = retrieve_exercise_candidates(graph, "fractions.add", target_misconception_id="m1")

    assert [node.candidate_id for node in result] == ["c1", "c3"]


def test_denies_access_to_a_node_outside_visible_scopes() -> None:
    graph = ExerciseCandidateGraph(snapshot_version="v1", nodes=(
        _node("c1", access_scope="organization"),
    ))

    with pytest.raises(ExerciseCandidateAccessDeniedError):
        retrieve_exercise_candidates(graph, "fractions.add", visible_access_scopes=frozenset({"system"}))


def test_organization_scope_is_allowed_when_visible() -> None:
    graph = ExerciseCandidateGraph(snapshot_version="v1", nodes=(
        _node("c1", access_scope="organization"),
    ))

    result = retrieve_exercise_candidates(
        graph, "fractions.add", visible_access_scopes=frozenset({"organization"}),
    )

    assert [node.candidate_id for node in result] == ["c1"]


def test_private_teacher_node_denied_to_a_different_teacher() -> None:
    graph = ExerciseCandidateGraph(snapshot_version="v1", nodes=(
        _node("c1", access_scope="private_teacher", owner_id="teacher-a"),
    ))

    with pytest.raises(ExerciseCandidateAccessDeniedError):
        retrieve_exercise_candidates(
            graph, "fractions.add",
            visible_access_scopes=frozenset({"private_teacher"}),
            requester_id="teacher-b",
        )


def test_private_teacher_node_allowed_to_its_own_owner() -> None:
    graph = ExerciseCandidateGraph(snapshot_version="v1", nodes=(
        _node("c1", access_scope="private_teacher", owner_id="teacher-a"),
    ))

    result = retrieve_exercise_candidates(
        graph, "fractions.add",
        visible_access_scopes=frozenset({"private_teacher"}),
        requester_id="teacher-a",
    )

    assert [node.candidate_id for node in result] == ["c1"]


def test_graph_and_nodes_are_immutable() -> None:
    graph = ExerciseCandidateGraph(snapshot_version="v1", nodes=(_node("c1"),))

    with pytest.raises(Exception):  # noqa: B017, PT011 -- pydantic frozen-model error
        graph.nodes[0].candidate_id = "changed"  # type: ignore[misc]
