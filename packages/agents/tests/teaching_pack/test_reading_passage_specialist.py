from __future__ import annotations

import pytest

from packages.agents.teaching_pack.specialists.reading_passage_specialist import (
    NoGroundedPassageError,
    generate_reading_passage_artifact,
)


def _lesson_plan() -> dict[str, object]:
    return {
        "topic": "Fractions",
        "subject": "Math",
        "grade_level": "Grade 5",
        "locale": "en",
        "learning_objectives": [{"description": "Identify equivalent fractions."}],
    }


def _research_brief() -> dict[str, object]:
    return {"sources": [{"title": "Fractions Guide", "excerpt": "Equivalent fractions represent the same value."}]}


def test_reading_passage_is_grounded_and_keeps_answers_in_metadata() -> None:
    artifact = generate_reading_passage_artifact(_lesson_plan(), _research_brief())

    assert artifact["sections"][0]["content"] == "Equivalent fractions represent the same value."
    assert artifact["metadata"]["passage_source"] == "Fractions Guide"
    assert artifact["metadata"]["comprehension_questions"][0]["answer"] == "Identify equivalent fractions."
    assert "answer" not in artifact["sections"][0]


def test_reading_passage_fails_closed_without_grounded_excerpt() -> None:
    with pytest.raises(NoGroundedPassageError):
        generate_reading_passage_artifact(_lesson_plan(), {"sources": []})


def test_reading_passage_scorecard_has_source_and_identity_evidence() -> None:
    artifact = generate_reading_passage_artifact(_lesson_plan(), _research_brief())

    assert artifact["metadata"]["reading_passage_scorecard"] == {
        "source_grounding": 1.0,
        "objective_coverage": 1.0,
        "question_identity": 1.0,
        "answer_separation": 1.0,
    }
