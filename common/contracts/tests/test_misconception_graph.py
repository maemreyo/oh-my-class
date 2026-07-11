from __future__ import annotations

import pytest

from common.contracts.claim_evidence import ClaimEvidence
from common.contracts.misconception_graph import (
    MisconceptionAccessDeniedError,
    MisconceptionGraph,
    MisconceptionNode,
    MisconceptionUngroundedError,
    retrieve_misconceptions,
)


def _grounded_evidence(claim_id: str = "claim-1") -> ClaimEvidence:
    return ClaimEvidence(
        claim_id=claim_id,
        claim_text="Students often add numerators and denominators directly.",
        risk_level="high",
        citation_ids=["source-1"],
        verification_status="VERIFIED",
    )


def _node(
    misconception_id: str,
    knowledge_component_id: str = "fractions.add",
    evidence: tuple[ClaimEvidence, ...] = (),
    access_scope: str = "system",
    owner_id: str | None = None,
) -> MisconceptionNode:
    return MisconceptionNode(
        misconception_id=misconception_id,
        knowledge_component_id=knowledge_component_id,
        description=misconception_id,
        evidence=evidence,
        access_scope=access_scope,
        owner_id=owner_id,
    )


def test_retrieval_is_deterministic_and_sorted_by_id() -> None:
    graph = MisconceptionGraph(snapshot_version="v1", nodes=(
        _node("zed-misconception"),
        _node("alpha-misconception"),
    ))

    result = retrieve_misconceptions(graph, "fractions.add", require_grounded_evidence=False)

    assert [node.misconception_id for node in result] == ["alpha-misconception", "zed-misconception"]
    assert retrieve_misconceptions(graph, "fractions.add", require_grounded_evidence=False) == result


def test_retrieval_filters_by_knowledge_component() -> None:
    graph = MisconceptionGraph(snapshot_version="v1", nodes=(
        _node("m1", knowledge_component_id="fractions.add"),
        _node("m2", knowledge_component_id="fractions.subtract"),
    ))

    result = retrieve_misconceptions(graph, "fractions.subtract", require_grounded_evidence=False)

    assert [node.misconception_id for node in result] == ["m2"]


def test_unknown_knowledge_component_returns_empty_not_an_error() -> None:
    graph = MisconceptionGraph(snapshot_version="v1", nodes=(_node("m1"),))

    result = retrieve_misconceptions(graph, "no-such-component")

    assert result == ()


def test_high_risk_misconception_without_citation_fails_closed() -> None:
    ungrounded = ClaimEvidence(
        claim_id="claim-1",
        claim_text="Students often add numerators and denominators directly.",
        risk_level="high",
        citation_ids=[],
        verification_status="UNCERTAIN",
    )
    graph = MisconceptionGraph(snapshot_version="v1", nodes=(
        _node("m1", evidence=(ungrounded,)),
    ))

    with pytest.raises(MisconceptionUngroundedError):
        retrieve_misconceptions(graph, "fractions.add")


def test_high_risk_misconception_with_grounded_evidence_is_returned() -> None:
    graph = MisconceptionGraph(snapshot_version="v1", nodes=(
        _node("m1", evidence=(_grounded_evidence(),)),
    ))

    result = retrieve_misconceptions(graph, "fractions.add")

    assert [node.misconception_id for node in result] == ["m1"]


def test_low_risk_ungrounded_claim_does_not_fail_closed() -> None:
    low_risk = ClaimEvidence(
        claim_id="claim-1",
        claim_text="A commonly seen slip.",
        risk_level="low",
        citation_ids=[],
        verification_status="UNCERTAIN",
    )
    graph = MisconceptionGraph(snapshot_version="v1", nodes=(
        _node("m1", evidence=(low_risk,)),
    ))

    result = retrieve_misconceptions(graph, "fractions.add")

    assert [node.misconception_id for node in result] == ["m1"]


def test_caller_can_opt_out_of_grounding_check() -> None:
    ungrounded = ClaimEvidence(
        claim_id="claim-1",
        claim_text="Students often add numerators and denominators directly.",
        risk_level="high",
        citation_ids=[],
        verification_status="UNCERTAIN",
    )
    graph = MisconceptionGraph(snapshot_version="v1", nodes=(
        _node("m1", evidence=(ungrounded,)),
    ))

    result = retrieve_misconceptions(graph, "fractions.add", require_grounded_evidence=False)

    assert [node.misconception_id for node in result] == ["m1"]


def test_denies_access_to_a_node_outside_visible_scopes() -> None:
    graph = MisconceptionGraph(snapshot_version="v1", nodes=(
        _node("m1", access_scope="organization"),
    ))

    with pytest.raises(MisconceptionAccessDeniedError):
        retrieve_misconceptions(graph, "fractions.add", visible_access_scopes=frozenset({"system"}))


def test_organization_scope_is_allowed_when_visible() -> None:
    graph = MisconceptionGraph(snapshot_version="v1", nodes=(
        _node("m1", access_scope="organization"),
    ))

    result = retrieve_misconceptions(
        graph, "fractions.add", visible_access_scopes=frozenset({"organization"}), require_grounded_evidence=False,
    )

    assert [node.misconception_id for node in result] == ["m1"]


def test_private_teacher_node_denied_to_a_different_teacher() -> None:
    graph = MisconceptionGraph(snapshot_version="v1", nodes=(
        _node("m1", access_scope="private_teacher", owner_id="teacher-a"),
    ))

    with pytest.raises(MisconceptionAccessDeniedError):
        retrieve_misconceptions(
            graph, "fractions.add",
            visible_access_scopes=frozenset({"private_teacher"}),
            requester_id="teacher-b",
            require_grounded_evidence=False,
        )


def test_private_teacher_node_allowed_to_its_own_owner() -> None:
    graph = MisconceptionGraph(snapshot_version="v1", nodes=(
        _node("m1", access_scope="private_teacher", owner_id="teacher-a"),
    ))

    result = retrieve_misconceptions(
        graph, "fractions.add",
        visible_access_scopes=frozenset({"private_teacher"}),
        requester_id="teacher-a",
        require_grounded_evidence=False,
    )

    assert [node.misconception_id for node in result] == ["m1"]


def test_graph_and_nodes_are_immutable() -> None:
    graph = MisconceptionGraph(snapshot_version="v1", nodes=(_node("m1"),))

    with pytest.raises(Exception):  # noqa: B017, PT011 -- pydantic frozen-model error
        graph.nodes[0].misconception_id = "changed"  # type: ignore[misc]
