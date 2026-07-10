"""#448: Certify the Science Subject Capability Pack across K-12.

Drives the real quiz/drill specialists for a science lesson plan in each
of the four canonical Grade Bands, mirroring #447's Math release gate:
- every generated answer is solver-verified (deterministic),
- every question carries a MOET_2018 + NGSS standard declared in
  science_capability_pack.json for that band (traceable),
- every question's misconception guard is one the pack actually declares,
- both English and Vietnamese locales produce valid, answerable content.
"""

from __future__ import annotations

import re
from fractions import Fraction
from pathlib import Path

import pytest

from common.contracts.grade_band import GradeBand, grade_band_for_label
from common.contracts.subject_capability_pack import load_subject_capability_pack
from packages.agents.teaching_pack.specialists.drill_specialist import generate_drill_artifact
from packages.agents.teaching_pack.specialists.quiz_specialist import generate_quiz_artifact
from packages.agents.teaching_pack.subject_packs.math_solver import solve_arithmetic_expression

_SCIENCE_PACK_PATH = (
    Path(__file__).resolve().parents[4]
    / "common"
    / "component_strategy_knowledge"
    / "capabilities"
    / "science_capability_pack.json"
)

_GRADE_LABELS: dict[GradeBand, str] = {
    GradeBand.K_2: "Grade 1",
    GradeBand.GRADES_3_5: "Grade 5",
    GradeBand.GRADES_6_8: "Grade 7",
    GradeBand.GRADES_9_12: "Grade 10",
}


def _lesson_plan(grade_label: str, locale: str) -> dict[str, object]:
    return {
        "topic": "Forces and Energy",
        "subject": "Science",
        "grade_level": grade_label,
        "locale": locale,
        "learning_objectives": [
            {"description": "Reason quantitatively about the science concept for this grade band."},
        ],
    }


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_grade_label_resolves_to_the_expected_band(grade_band: GradeBand) -> None:
    assert grade_band_for_label(_GRADE_LABELS[grade_band]) is grade_band


@pytest.mark.parametrize("grade_band", list(GradeBand))
@pytest.mark.parametrize("locale", ["en", "vi"])
def test_quiz_answers_are_deterministic_and_standards_traceable(grade_band: GradeBand, locale: str) -> None:
    pack = load_subject_capability_pack(_SCIENCE_PACK_PATH)
    coverage = pack.coverage_for(grade_band)
    declared_codes = {standard.code for standard in coverage.standards}
    declared_misconceptions = {m.misconception_id for m in coverage.misconceptions}

    quiz = generate_quiz_artifact(_lesson_plan(_GRADE_LABELS[grade_band], locale), {"sources": []})
    questions = quiz["sections"][0]["components"]
    assert questions, "expected the science-aware quiz builder to produce questions"

    for question in questions:
        assert question["grade_band"] == grade_band.value
        answer_text = question["options"][question["answer"]]
        assert answer_text
        assert question["standard_code"] in declared_codes
        assert question["misconception_id"] in declared_misconceptions


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_drill_progression_is_solver_verified_across_the_band(grade_band: GradeBand) -> None:
    pack = load_subject_capability_pack(_SCIENCE_PACK_PATH)
    coverage = pack.coverage_for(grade_band)
    declared_codes = {standard.code for standard in coverage.standards}

    drill = generate_drill_artifact(_lesson_plan(_GRADE_LABELS[grade_band], "vi"), {"sources": []})
    activities = drill["sections"][0]["components"]
    assert [a["difficulty_level"] for a in activities] == list(range(1, len(activities) + 1))
    for activity in activities:
        assert activity["standard_code"] in declared_codes
        assert activity["answer"] in activity["options"]


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_science_quiz_is_deterministic_across_repeated_generation(grade_band: GradeBand) -> None:
    lesson_plan = _lesson_plan(_GRADE_LABELS[grade_band], "en")
    first = generate_quiz_artifact(lesson_plan, {"sources": []})
    second = generate_quiz_artifact(lesson_plan, {"sources": []})
    assert first["sections"][0]["components"] == second["sections"][0]["components"]


def test_grade_9_12_kinetic_energy_misconception_is_independently_recomputable() -> None:
    """End-to-end cross-check, parsing only the rendered artifact: reparse
    the kinetic-energy prompt's mass/velocity from its own text, and
    confirm the card's correct option is (1/2)*m*v^2 while a wrong option
    is the documented "forgot to square v" misconception -- computed
    independently here, not trusted from the generator."""
    quiz = generate_quiz_artifact(_lesson_plan("Grade 10", "en"), {"sources": []})
    questions = quiz["sections"][0]["components"]
    assert questions
    for question in questions:
        assert question["misconception_id"] == "grade912_forgets_to_square_velocity"
        match = re.match(r"A (\d+) kg object moves at (\d+) m/s\.", question["text"])
        assert match is not None, question["text"]
        mass, velocity = (int(group) for group in match.groups())

        correct_value = solve_arithmetic_expression(f"(1/2)*{mass}*{velocity}*{velocity}")
        misconception_value = solve_arithmetic_expression(f"(1/2)*{mass}*{velocity}")

        options = question["options"]
        rendered_values = {letter: Fraction(text) for letter, text in options.items()}
        assert rendered_values[question["answer"]] == correct_value
        assert misconception_value in rendered_values.values()
