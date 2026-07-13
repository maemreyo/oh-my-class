from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.content_intelligence_graph.example import (
    ExampleAccessDeniedError,
    ExampleGraph,
    ExampleNode,
    retrieve_examples,
)


def _node(example_id: str, kc: str = "kc.1", access_scope: str = "system", owner_id: str | None = None) -> ExampleNode:
    return ExampleNode(
        example_id=example_id,
        knowledge_component_id=kc,
        prompt_en="Show 5 x 7 as 5 groups of 7 objects.",
        prompt_vi="Biểu diễn 5 x 7 dưới dạng 5 nhóm, mỗi nhóm 7 đồ vật.",
        access_scope=access_scope,
        owner_id=owner_id,
    )


def test_retrieve_examples_is_deterministically_ordered() -> None:
    graph = ExampleGraph(snapshot_version="v1", nodes=(_node("ex.b"), _node("ex.a")))
    result = retrieve_examples(graph, "kc.1")
    assert [n.example_id for n in result] == ["ex.a", "ex.b"]


def test_retrieve_examples_empty_result_is_not_an_error() -> None:
    graph = ExampleGraph(snapshot_version="v1", nodes=(_node("ex.a", kc="kc.other"),))
    assert retrieve_examples(graph, "kc.1") == ()


def test_retrieve_examples_denies_out_of_scope_node() -> None:
    graph = ExampleGraph(snapshot_version="v1", nodes=(_node("ex.a", access_scope="organization"),))
    with pytest.raises(ExampleAccessDeniedError):
        retrieve_examples(graph, "kc.1")


def test_retrieve_examples_denies_other_teachers_private_node() -> None:
    graph = ExampleGraph(
        snapshot_version="v1",
        nodes=(_node("ex.a", access_scope="private_teacher", owner_id="teacher-1"),),
    )
    with pytest.raises(ExampleAccessDeniedError):
        retrieve_examples(
            graph, "kc.1",
            visible_access_scopes=frozenset({"private_teacher"}),
            requester_id="teacher-2",
        )


def test_example_graph_rejects_duplicate_ids() -> None:
    with pytest.raises(ValidationError, match="duplicate node id"):
        ExampleGraph(snapshot_version="v1", nodes=(_node("dup"), _node("dup")))


def test_example_node_is_frozen() -> None:
    node = _node("ex.a")
    with pytest.raises(Exception):  # noqa: B017, PT011
        node.prompt_en = "changed"  # type: ignore[misc]
