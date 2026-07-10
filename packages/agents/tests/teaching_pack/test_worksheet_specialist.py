from __future__ import annotations

import pytest

from packages.agents.teaching_pack.specialists.worksheet_specialist import (
    NoPracticeObjectivesError,
    build_worksheet_questions,
    generate_worksheet_artifact,
    score_worksheet,
)
from packages.quality.layer1_schema.component_gate import validate_component_minimums


def _lesson_plan() -> dict[str, object]:
    return {
        "topic": "Equivalent Fractions",
        "subject": "Math",
        "grade_level": "Grade 5",
        "locale": "en",
        "learning_objectives": [
            {"description": "Identify equivalent fractions."},
            {"description": "Generate equivalent fractions."},
        ],
    }


def test_worksheet_questions_are_stable_and_cover_approved_objectives() -> None:
    first = build_worksheet_questions(_lesson_plan())
    second = build_worksheet_questions(_lesson_plan())

    assert len(first) == 3
    assert [question["id"] for question in first] == [question["id"] for question in second]
    assert "Identify equivalent fractions." in first[0]["text"]
    assert "Generate equivalent fractions." in first[1]["text"]


def test_worksheet_fails_closed_without_objectives() -> None:
    with pytest.raises(NoPracticeObjectivesError):
        generate_worksheet_artifact({"topic": "Empty"}, {"sources": []})


def test_generated_worksheet_meets_component_gate_and_keeps_answers_out_of_section_questions() -> None:
    artifact = generate_worksheet_artifact(_lesson_plan(), {"sources": []})
    questions = artifact["sections"][0]["components"]

    assert validate_component_minimums(artifact) == []
    assert all(question["type"] == "question_card" for question in questions)
    assert "questions" not in artifact["sections"][0]


def test_worksheet_scorecard_covers_practice_dimensions() -> None:
    questions = build_worksheet_questions(_lesson_plan())
    scorecard = score_worksheet(questions, objective_count=2)

    assert scorecard.scaffolding == 1.0
    assert scorecard.progression == 1.0
    assert scorecard.retrieval == 1.0
    assert scorecard.feedback == 1.0
    assert scorecard.objective_coverage == 1.0
