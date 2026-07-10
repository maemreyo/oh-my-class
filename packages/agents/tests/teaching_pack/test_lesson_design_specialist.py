from __future__ import annotations

import pytest

from packages.agents.teaching_pack.specialists.lesson_design_specialist import (
    NoApprovedLessonDesignError,
    build_lesson_sections,
    generate_lesson_design_artifact,
    score_lesson_design,
)


def _lesson_plan() -> dict[str, object]:
    return {
        "topic": "Equivalent Fractions",
        "locale": "en",
        "duration_minutes": 45,
        "methodology": "concrete-representational-abstract",
        "learning_objectives": [
            {"description": "Identify equivalent fractions."},
            {"description": "Generate an equivalent fraction."},
        ],
        "learning_plan": {
            "engage": "Compare two fraction strips.",
            "practice": {"activity": "Model equivalent fractions with drawings."},
        },
    }


def test_build_lesson_sections_copies_approved_objectives_and_phases() -> None:
    sections = build_lesson_sections(_lesson_plan())

    assert [section["id"] for section in sections] == [
        "objective-1", "objective-2", "phase-1", "phase-2",
    ]
    assert sections[0]["content"] == "Identify equivalent fractions."
    assert sections[-1]["content"] == "Model equivalent fractions with drawings."


def test_generate_lesson_design_fails_closed_without_approved_objectives() -> None:
    with pytest.raises(NoApprovedLessonDesignError):
        generate_lesson_design_artifact({"learning_plan": {"engage": "Guess."}}, {"sources": []})


def test_lesson_design_scorecard_has_all_authority_dimensions() -> None:
    lesson_plan = _lesson_plan()
    scorecard = score_lesson_design(lesson_plan, build_lesson_sections(lesson_plan))

    assert scorecard.objective_coverage == 1.0
    assert scorecard.instructional_sequence == 1.0
    assert scorecard.pacing == 1.0
    assert scorecard.cognitive_load == 1.0
    assert scorecard.methodology_fidelity == 1.0


def test_generated_lesson_is_renderer_compatible_and_grounded() -> None:
    artifact = generate_lesson_design_artifact(_lesson_plan(), {
        "sources": [{"title": "Fractions guide", "excerpt": "Equivalent fractions have the same value."}],
    })

    assert artifact["artifact_type"] == "lesson"
    assert artifact["accessibility"] == {"language": "en"}
    assert len(artifact["sections"]) == 4
    assert set(artifact["metadata"]["lesson_design_scorecard"]) == {
        "objective_coverage", "instructional_sequence", "pacing", "cognitive_load", "methodology_fidelity",
    }
    assert artifact["metadata"]["research_traces"][0]["source_ref"] == "Fractions guide"
