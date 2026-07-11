"""#450: Certify the Humanities and Social Studies Capability Pack across K-12.

Drives the real quiz/drill specialists for a humanities lesson plan in each
of the four canonical Grade Bands, mirroring #447/#448/#449's release gates:
- every question carries a MOET_2018 + CCSS standard declared in
  humanities_capability_pack.json for that band (traceable),
- every question's misconception guard is one the pack actually declares,
- both English and Vietnamese locales produce valid, answerable content,
- one overlay domain per band -- civics (K-2), geography (3-5), history/
  sourcing (6-8), literature/theme (9-12) -- so all four domains named in
  #450's AC are certified across the release.
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
    / "humanities_capability_pack.json"
)

_GRADE_LABELS: dict[GradeBand, str] = {
    GradeBand.K_2: "Grade 1",
    GradeBand.GRADES_3_5: "Grade 5",
    GradeBand.GRADES_6_8: "Grade 7",
    GradeBand.GRADES_9_12: "Grade 10",
}

_EXPECTED_MISCONCEPTION_BY_BAND: dict[GradeBand, str] = {
    GradeBand.K_2: "k2_thinks_rules_exist_only_to_punish",
    GradeBand.GRADES_3_5: "grade35_confuses_map_up_with_forward_direction",
    GradeBand.GRADES_6_8: "grade68_assumes_old_document_is_always_primary_source",
    GradeBand.GRADES_9_12: "grade912_confuses_plot_summary_with_theme",
}


def _lesson_plan(grade_label: str, locale: str) -> dict[str, object]:
    return {
        "topic": "Humanities and Social Studies",
        "subject": "Humanities_and_Social_Studies",
        "grade_level": grade_label,
        "locale": locale,
        "learning_objectives": [
            {"description": "Reason about the humanities overlay concept for this grade band."},
        ],
    }


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_grade_label_resolves_to_the_expected_band(grade_band: GradeBand) -> None:
    assert grade_band_for_label(_GRADE_LABELS[grade_band]) is grade_band


@pytest.mark.parametrize("grade_band", list(GradeBand))
@pytest.mark.parametrize("locale", ["en", "vi"])
def test_quiz_answers_are_standards_traceable(grade_band: GradeBand, locale: str) -> None:
    pack = load_subject_capability_pack(_PACK_PATH)
    coverage = pack.coverage_for(grade_band)
    declared_codes = {standard.code for standard in coverage.standards}
    declared_misconceptions = {m.misconception_id for m in coverage.misconceptions}

    quiz = generate_quiz_artifact(_lesson_plan(_GRADE_LABELS[grade_band], locale), {"sources": []})
    questions = quiz["sections"][0]["components"]
    assert questions, "expected the humanities-aware quiz builder to produce questions"

    for question in questions:
        assert question["grade_band"] == grade_band.value
        answer_text = question["options"][question["answer"]]
        assert answer_text
        assert question["standard_code"] in declared_codes
        assert question["misconception_id"] in declared_misconceptions
        assert question["misconception_id"] == _EXPECTED_MISCONCEPTION_BY_BAND[grade_band]


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_drill_progression_is_governed_across_the_band(grade_band: GradeBand) -> None:
    pack = load_subject_capability_pack(_PACK_PATH)
    coverage = pack.coverage_for(grade_band)
    declared_codes = {standard.code for standard in coverage.standards}

    drill = generate_drill_artifact(_lesson_plan(_GRADE_LABELS[grade_band], "vi"), {"sources": []})
    activities = drill["sections"][0]["components"]
    assert [a["difficulty_level"] for a in activities] == list(range(1, len(activities) + 1))
    for activity in activities:
        assert activity["standard_code"] in declared_codes
        assert activity["answer"] in activity["options"]


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_quiz_is_deterministic_across_repeated_generation(grade_band: GradeBand) -> None:
    lesson_plan = _lesson_plan(_GRADE_LABELS[grade_band], "en")
    first = generate_quiz_artifact(lesson_plan, {"sources": []})
    second = generate_quiz_artifact(lesson_plan, {"sources": []})
    assert first["sections"][0]["components"] == second["sections"][0]["components"]


def test_grade_6_8_source_item_never_labels_the_later_textbook_as_primary() -> None:
    """Cross-check the sourcing misconception guard end-to-end: the correct
    option must always be the eyewitness/contemporary account, never the
    later secondary summary, regardless of which locale renders it."""
    quiz = generate_quiz_artifact(_lesson_plan("Grade 7", "en"), {"sources": []})
    questions = quiz["sections"][0]["components"]
    assert questions
    for question in questions:
        assert question["misconception_id"] == "grade68_assumes_old_document_is_always_primary_source"
        answer_text = question["options"][question["answer"]].lower()
        assert "textbook" not in answer_text and "documentary" not in answer_text
