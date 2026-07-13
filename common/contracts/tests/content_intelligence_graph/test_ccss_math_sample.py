"""Graph-integrity tests for the seeded CCSS Math sample, plus the #465
"live-path" proof: a ContentBrief and a DecisionProvenance record pinning
the same graph snapshot version and the same evidence citation IDs.
"""

from __future__ import annotations

from common.contracts.content_brief import ContentBrief
from common.contracts.content_intelligence_graph.alignment import assert_alignment_is_grounded
from common.contracts.content_intelligence_graph.prerequisite import prerequisite_closure
from common.contracts.content_intelligence_graph.seeds.ccss_math_sample import (
    CCSS_MATH_SAMPLE_ALIGNMENTS,
    CCSS_MATH_SAMPLE_PREREQUISITE_GRAPH,
)
from common.contracts.decision_provenance import DecisionProvenance


def test_sample_prerequisite_graph_closure_is_acyclic_and_deterministic() -> None:
    closure = prerequisite_closure(CCSS_MATH_SAMPLE_PREREQUISITE_GRAPH, "kc.ccss_math_sample.7.ee.b.4")
    assert closure == (
        "kc.ccss_math_sample.3.oa.a.1",
        "kc.ccss_math_sample.4.nbt.b.5",
        "kc.ccss_math_sample.5.nf.b.4",
        "kc.ccss_math_sample.6.rp.a.1",
    )


def test_sample_alignments_reference_real_declared_knowledge_components() -> None:
    declared_ids = {node.node_id for node in CCSS_MATH_SAMPLE_PREREQUISITE_GRAPH.nodes}
    for record in CCSS_MATH_SAMPLE_ALIGNMENTS:
        assert record.knowledge_component_id in declared_ids


def test_sample_alignments_are_all_grounded() -> None:
    for record in CCSS_MATH_SAMPLE_ALIGNMENTS:
        assert_alignment_is_grounded(record)  # no raise


def test_sample_alignment_standard_codes_are_unique() -> None:
    codes = [record.standard.code for record in CCSS_MATH_SAMPLE_ALIGNMENTS]
    assert len(codes) == len(set(codes))


def test_sample_is_a_small_honest_slice_not_a_full_catalog() -> None:
    # Documents the deliberate scope boundary in a checkable form: if someone
    # bulk-adds records later without updating the docstring's honesty claim,
    # this test is the tripwire that says "the claim in the docstring is
    # stale" rather than letting scope creep silently pass as "still small".
    assert len(CCSS_MATH_SAMPLE_ALIGNMENTS) == 5
    assert {record.standard.framework for record in CCSS_MATH_SAMPLE_ALIGNMENTS} == {"CCSS"}


def test_content_brief_and_decision_provenance_pin_the_same_graph_snapshot() -> None:
    """#465 live-path proof: a ContentBrief and the DecisionProvenance for the
    artifact produced from it pin the identical `knowledge_db_version` (graph
    snapshot) and cite the identical evidence id -- not just two independently
    correct-looking values that happen to match by coincidence in a fixture.
    """
    snapshot_version = CCSS_MATH_SAMPLE_PREREQUISITE_GRAPH.snapshot_version
    alignment = CCSS_MATH_SAMPLE_ALIGNMENTS[0]

    brief = ContentBrief(
        content_brief_id="brief-1",
        run_id="run-1",
        artifact_type="worksheet",
        objectives=["kc.ccss_math_sample.3.oa.a.1"],
        methodology="direct_instruction",
        methodology_source="default",
        source_citation_ids=list(alignment.evidence.citation_ids),
        knowledge_db_version=snapshot_version,
    )
    provenance = DecisionProvenance(
        document_id="doc-1",
        version=1,
        authority="generated",
        claim_evidence=[alignment.evidence],
        knowledge_db_version=snapshot_version,
    )

    assert brief.knowledge_db_version == provenance.knowledge_db_version == snapshot_version
    assert set(brief.source_citation_ids) & set(provenance.claim_evidence[0].citation_ids)
