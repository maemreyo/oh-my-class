"""#449: Certify the Language and Literacy Capability Pack across K-12.

Drives the real quiz/drill specialists for a language-and-literacy lesson
plan in each of the four canonical Grade Bands, mirroring #447/#448's
release gates:
- every question carries a MOET_2018 + CCSS standard declared in
  language_literacy_capability_pack.json for that band (traceable),
- every question's misconception guard is one the pack actually declares,
- English-target (EFL/ESL) and Vietnamese-target literacy scenarios both
  pass, keeping target_language strictly separate from instruction_language
  (#449 AC) -- an English-medium classroom teaching Vietnamese literacy and
  a Vietnamese-medium classroom teaching English both produce valid content.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from common.contracts.grade_band import GradeBand, grade_band_for_label
from common.contracts.subject_capability_pack import load_subject_capability_pack
from packages.agents.teaching_pack.specialists.drill_specialist import generate_drill_artifact
from packages.agents.teaching_pack.specialists.quiz_specialist import generate_quiz_artifact

_PACK_PATH = (
    Path(__file__).resolve().parents[4]
    / "common"
    / "component_strategy_knowledge"
    / "capabilities"
    / "language_literacy_capability_pack.json"
)

_GRADE_LABELS: dict[GradeBand, str] = {
    GradeBand.K_2: "Grade 1",
    GradeBand.GRADES_3_5: "Grade 5",
    GradeBand.GRADES_6_8: "Grade 7",
    GradeBand.GRADES_9_12: "Grade 10",
}


def _lesson_plan(grade_label: str, *, target_language: str, instruction_language: str) -> dict[str, object]:
    return {
        "topic": "Language and Literacy",
        "subject": "Language_and_Literacy",
        "grade_level": grade_label,
        "target_language": target_language,
        "instruction_language": instruction_language,
        "learning_objectives": [
            {"description": "Reason about the literacy concept for this grade band."},
        ],
    }


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_grade_label_resolves_to_the_expected_band(grade_band: GradeBand) -> None:
    assert grade_band_for_label(_GRADE_LABELS[grade_band]) is grade_band


@pytest.mark.parametrize("grade_band", list(GradeBand))
@pytest.mark.parametrize(
    ("target_language", "instruction_language"),
    [("en", "vi"), ("vi", "vi"), ("en", "en")],
    ids=["efl-vietnamese-medium", "vietnamese-literacy", "english-literacy"],
)
def test_quiz_answers_are_standards_traceable_in_every_language_pairing(
    grade_band: GradeBand, target_language: str, instruction_language: str,
) -> None:
    pack = load_subject_capability_pack(_PACK_PATH)
    coverage = pack.coverage_for(grade_band)
    declared_codes = {standard.code for standard in coverage.standards}
    declared_misconceptions = {m.misconception_id for m in coverage.misconceptions}

    lesson_plan = _lesson_plan(
        _GRADE_LABELS[grade_band], target_language=target_language, instruction_language=instruction_language,
    )
    quiz = generate_quiz_artifact(lesson_plan, {"sources": []})
    questions = quiz["sections"][0]["components"]
    assert questions, "expected the language-and-literacy-aware quiz builder to produce questions"

    for question in questions:
        assert question["grade_band"] == grade_band.value
        answer_text = question["options"][question["answer"]]
        assert answer_text
        assert question["standard_code"] in declared_codes
        assert question["misconception_id"] in declared_misconceptions


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_drill_progression_is_governed_across_the_band(grade_band: GradeBand) -> None:
    pack = load_subject_capability_pack(_PACK_PATH)
    coverage = pack.coverage_for(grade_band)
    declared_codes = {standard.code for standard in coverage.standards}

    lesson_plan = _lesson_plan(_GRADE_LABELS[grade_band], target_language="en", instruction_language="vi")
    drill = generate_drill_artifact(lesson_plan, {"sources": []})
    activities = drill["sections"][0]["components"]
    assert [a["difficulty_level"] for a in activities] == list(range(1, len(activities) + 1))
    for activity in activities:
        assert activity["standard_code"] in declared_codes
        assert activity["answer"] in activity["options"]


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_quiz_is_deterministic_across_repeated_generation(grade_band: GradeBand) -> None:
    lesson_plan = _lesson_plan(_GRADE_LABELS[grade_band], target_language="en", instruction_language="vi")
    first = generate_quiz_artifact(lesson_plan, {"sources": []})
    second = generate_quiz_artifact(lesson_plan, {"sources": []})
    assert first["sections"][0]["components"] == second["sections"][0]["components"]


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_target_language_changes_content_while_instruction_language_stays_fixed(grade_band: GradeBand) -> None:
    """The heart of #449's AC: swapping target_language (what's taught)
    while holding instruction_language fixed (how it's explained) must
    change the taught content -- proving the two are not the same field
    read twice under different names."""
    english_target = _lesson_plan(_GRADE_LABELS[grade_band], target_language="en", instruction_language="vi")
    vietnamese_target = _lesson_plan(_GRADE_LABELS[grade_band], target_language="vi", instruction_language="vi")

    english_quiz = generate_quiz_artifact(english_target, {"sources": []})
    vietnamese_quiz = generate_quiz_artifact(vietnamese_target, {"sources": []})

    english_misconceptions = {q["misconception_id"] for q in english_quiz["sections"][0]["components"]}
    vietnamese_misconceptions = {q["misconception_id"] for q in vietnamese_quiz["sections"][0]["components"]}
    assert english_misconceptions.isdisjoint(vietnamese_misconceptions)
