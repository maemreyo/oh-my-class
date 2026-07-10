from __future__ import annotations

import pytest

from packages.agents.teaching_pack.specialists.recap_specialist import (
    NoGroundedConceptsError,
    compress_recap,
    generate_recap_artifact,
    score_recap,
)


def _lesson_plan_with_dict_objectives() -> dict[str, object]:
    """The canonical shape (`common/contracts/lesson_plan.py::LearningObjective`)."""
    return {
        "topic": "Equivalent Fractions",
        "learning_objectives": [
            {"description": "Students can identify equivalent fractions.", "bloom_level": "understand"},
            {"description": "Students can generate an equivalent fraction.", "bloom_level": "apply"},
        ],
    }


def _research_brief_with_excerpts() -> dict[str, object]:
    return {
        "sources": [
            {
                "title": "NCTM Fractions Guide",
                "url": "https://example.org/nctm",
                "excerpt": "Equivalent fractions represent the same value. They can be found by multiplying.",
            },
            {"title": "No excerpt source", "url": "https://example.org/none"},
        ],
    }


def test_compress_recap_retains_objectives_and_grounded_findings_only() -> None:
    concepts = compress_recap(_lesson_plan_with_dict_objectives(), _research_brief_with_excerpts())

    assert [c.source_type for c in concepts] == ["objective", "objective", "research_finding"]
    assert concepts[0].text == "Students can identify equivalent fractions."
    assert concepts[2].text == "Equivalent fractions represent the same value."
    assert concepts[2].source_ref == "NCTM Fractions Guide"


def test_compress_recap_tolerates_plain_string_objectives() -> None:
    lesson_plan = {"learning_objectives": ["Explain the water cycle."]}
    concepts = compress_recap(lesson_plan, {"sources": []})

    assert len(concepts) == 1
    assert concepts[0].text == "Explain the water cycle."


def test_compress_recap_is_bounded_by_max_concepts() -> None:
    lesson_plan = {"learning_objectives": [{"description": f"Objective {i}"} for i in range(10)]}
    concepts = compress_recap(lesson_plan, {"sources": []}, max_concepts=3)

    assert len(concepts) == 3


def test_generate_recap_artifact_raises_when_nothing_grounded_to_retain() -> None:
    with pytest.raises(NoGroundedConceptsError):
        generate_recap_artifact({"learning_objectives": []}, {"sources": []})


def test_generate_recap_artifact_traces_every_retained_concept_to_its_source() -> None:
    artifact = generate_recap_artifact(_lesson_plan_with_dict_objectives(), _research_brief_with_excerpts())

    assert artifact["artifact_type"] == "recap"
    # One section per concept (packages/renderer/src/agent-renderer.ts::recapData
    # flattens one section into one recap card; it has no per-section items list).
    sections = artifact["sections"]
    traces = artifact["metadata"]["retained_concept_traces"]
    assert len(sections) == len(traces)
    assert all(section["content"] for section in sections)
    traced_entity_ids = {trace["entity_id"] for trace in traces}
    assert traced_entity_ids == {section["id"] for section in sections}
    assert all(trace["source_ref"] for trace in traces)


def test_generate_recap_artifact_includes_a_scorecard_with_all_four_dimensions() -> None:
    artifact = generate_recap_artifact(_lesson_plan_with_dict_objectives(), _research_brief_with_excerpts())

    scorecard = artifact["metadata"]["recap_scorecard"]
    assert set(scorecard) == {"compression_ratio", "recall_utility", "coverage", "consistency"}
    assert scorecard["consistency"] is True
    assert 0.0 < scorecard["recall_utility"] <= 1.0


def test_score_recap_recall_utility_only_counts_objectives_not_findings() -> None:
    lesson_plan = _lesson_plan_with_dict_objectives()  # 2 objectives
    research_brief = _research_brief_with_excerpts()  # 1 grounded finding
    concepts = compress_recap(lesson_plan, research_brief, max_concepts=1)  # only the first objective retained

    scorecard = score_recap(lesson_plan, research_brief, concepts)

    assert scorecard.recall_utility == 0.5  # 1 of 2 objectives
    assert scorecard.coverage < 1.0  # objectives + findings not all retained


def test_score_recap_flags_inconsistency_on_duplicate_entity_ids() -> None:
    lesson_plan = _lesson_plan_with_dict_objectives()
    concepts = compress_recap(lesson_plan, {"sources": []})
    duplicated = [concepts[0], concepts[0]]

    scorecard = score_recap(lesson_plan, {"sources": []}, duplicated)

    assert scorecard.consistency is False
