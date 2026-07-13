from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.content_intelligence_graph.terminology import (
    TerminologyAccessDeniedError,
    TerminologyGraph,
    TerminologyNode,
    retrieve_terminology,
)


def _node(term_id: str, kc: str = "kc.1", access_scope: str = "system", owner_id: str | None = None) -> TerminologyNode:
    return TerminologyNode(
        term_id=term_id,
        knowledge_component_id=kc,
        term_en="ratio",
        term_vi="tỉ số",
        definition_en="a comparison of two quantities",
        definition_vi="so sánh giữa hai đại lượng",
        access_scope=access_scope,
        owner_id=owner_id,
    )


def test_retrieve_terminology_is_deterministically_ordered() -> None:
    graph = TerminologyGraph(snapshot_version="v1", nodes=(_node("term.b"), _node("term.a")))
    result = retrieve_terminology(graph, "kc.1")
    assert [n.term_id for n in result] == ["term.a", "term.b"]


def test_retrieve_terminology_empty_result_is_not_an_error() -> None:
    graph = TerminologyGraph(snapshot_version="v1", nodes=(_node("term.a", kc="kc.other"),))
    assert retrieve_terminology(graph, "kc.1") == ()


def test_retrieve_terminology_denies_out_of_scope_node() -> None:
    graph = TerminologyGraph(snapshot_version="v1", nodes=(_node("term.a", access_scope="organization"),))
    with pytest.raises(TerminologyAccessDeniedError):
        retrieve_terminology(graph, "kc.1")


def test_retrieve_terminology_denies_other_teachers_private_node() -> None:
    graph = TerminologyGraph(
        snapshot_version="v1",
        nodes=(_node("term.a", access_scope="private_teacher", owner_id="teacher-1"),),
    )
    with pytest.raises(TerminologyAccessDeniedError):
        retrieve_terminology(
            graph, "kc.1",
            visible_access_scopes=frozenset({"private_teacher"}),
            requester_id="teacher-2",
        )


def test_retrieve_terminology_allows_same_teacher_private_node() -> None:
    graph = TerminologyGraph(
        snapshot_version="v1",
        nodes=(_node("term.a", access_scope="private_teacher", owner_id="teacher-1"),),
    )
    result = retrieve_terminology(
        graph, "kc.1",
        visible_access_scopes=frozenset({"private_teacher"}),
        requester_id="teacher-1",
    )
    assert [n.term_id for n in result] == ["term.a"]


def test_terminology_graph_rejects_duplicate_ids() -> None:
    with pytest.raises(ValidationError, match="duplicate node id"):
        TerminologyGraph(snapshot_version="v1", nodes=(_node("dup"), _node("dup")))


def test_terminology_node_is_frozen() -> None:
    node = _node("term.a")
    with pytest.raises(Exception):  # noqa: B017, PT011
        node.term_en = "changed"  # type: ignore[misc]
