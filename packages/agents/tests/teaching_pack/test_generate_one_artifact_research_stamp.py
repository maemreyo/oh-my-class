"""Producer side of the fact_check seam: generation stamps the grounded corpus.

``generate_one_artifact`` must copy the run's grounded research sources (those with a
fetched body) onto ``artifact.metadata.research_sources`` so the Layer-2 gate can
cross-reference. Only grounded sources are carried; content-less sources are dropped.
"""

from __future__ import annotations

from packages.agents.teaching_pack.generate_one_artifact import (
    _stamp_pedagogy_context,
    _stamp_research_sources,
)


def test_stamp_carries_only_grounded_sources() -> None:
    chunk: dict[str, object] = {"artifact_type": "lesson", "metadata": {"duration": 30}}
    research_brief = {
        "sources": [
            {"title": "A", "url": "https://a.edu", "excerpt": "grounded body A"},
            {"title": "B", "url": "https://b.gov", "excerpt": None},  # not fetched
            {"title": "C", "url": "https://c.org", "excerpt": "grounded body C"},
        ]
    }

    _stamp_research_sources(chunk, research_brief)

    corpus = chunk["metadata"]["research_sources"]  # type: ignore[index]
    assert [s["title"] for s in corpus] == ["A", "C"]
    assert corpus[0] == {"title": "A", "content": "grounded body A", "url": "https://a.edu"}
    assert chunk["metadata"]["duration"] == 30  # existing metadata preserved


def test_stamp_is_fail_open_and_non_destructive() -> None:
    # No grounded sources -> do not add an empty research_sources key.
    chunk: dict[str, object] = {"metadata": {}}
    _stamp_research_sources(chunk, {"sources": [{"title": "B", "excerpt": None}]})
    assert "research_sources" not in chunk["metadata"]  # type: ignore[operator]

    # Never overwrite an existing corpus.
    chunk2: dict[str, object] = {"metadata": {"research_sources": [{"title": "pre"}]}}
    _stamp_research_sources(chunk2, {"sources": [{"title": "A", "excerpt": "body"}]})
    assert chunk2["metadata"]["research_sources"] == [{"title": "pre"}]  # type: ignore[index]


def test_pedagogy_stamp_carries_only_leakage_safe_subset() -> None:
    chunk: dict[str, object] = {"metadata": {}}
    lesson_plan = {
        "learning_objectives": ["Describe the water cycle"],
        "grade": 5,
        "teacher_script": "SECRET internal script",  # must NOT be carried
        "answer_key": "should never leak",
    }

    _stamp_pedagogy_context(chunk, lesson_plan)

    context = chunk["metadata"]["pedagogy_context"]  # type: ignore[index]
    assert context == {"learning_objectives": ["Describe the water cycle"], "grade": 5}
    assert "teacher_script" not in context
    assert "answer_key" not in context


def test_pedagogy_stamp_fail_open_when_no_safe_fields() -> None:
    chunk: dict[str, object] = {"metadata": {}}
    _stamp_pedagogy_context(chunk, {"teacher_script": "only unsafe fields"})
    assert "pedagogy_context" not in chunk["metadata"]  # type: ignore[operator]
