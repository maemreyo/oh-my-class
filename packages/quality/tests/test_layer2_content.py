"""Tests for Layer 2 content quality — methodology compliance gate.

Imports from the production module:
  packages.quality.layer2_content.methodology
"""
from __future__ import annotations

from packages.quality.layer2_content.methodology import (
    MethodologyGateResult,
    check_methodology_compliance,
)


def _build_vocab_lesson(include=None):
    include = include or {"film", "vocab", "phrasal", "questions", "roleplay"}
    sections = []
    if "film" in include:
        sections.append({"heading": "Warm-up", "components": [
            {"type": "film_clip_activity", "clips": [{"title": "Test", "description": "desc"}], "hunt_chips": ["arrive"]}  # noqa: E501
        ]})
    if "vocab" in include:
        sections.append({"heading": "Concept", "components": [
            {"type": "vocab_cluster", "title": "arrive/reach", "items": [
                {"word": "arrive", "definition": "reach destination"},
            ]}
        ]})
    if "phrasal" in include:
        sections.append({"heading": "Phrasal", "components": [
            {"type": "phrasal_verb_cluster", "groups": [{"label": "Leaving", "color": "a", "items": [  # noqa: E501
                {"verb": "set off", "meaning": "begin journey"}
            ]}]}
        ]})
    if "questions" in include:
        sections.append({"heading": "Practice", "components": [
            {"type": "question_card", "id": 1, "text": "Q?", "options": {"A": "a", "B": "b"},
             "answer": "B", "explain": "Because...", "wrong_reasons": {"A": "A is wrong"}}
        ]})
    if "roleplay" in include:
        sections.append({"heading": "Roleplay", "components": [
            {"type": "roleplay_script", "lines": [
                {"speaker": "A", "text": "We should [blank_1] soon."}
            ], "answer_key": ["set off"]}
        ]})
    return sections


class TestMethodologyCompliance:
    """Verify that check_methodology_compliance enforces tag-gated structural requirements."""

    def test_no_tags_always_passes(self):
        result = check_methodology_compliance([], [])
        assert isinstance(result, MethodologyGateResult)
        assert result.passed is True
        assert result.violations == []

    def test_no_tags_with_sections_still_passes(self):
        sections = _build_vocab_lesson()
        result = check_methodology_compliance(sections, [])
        assert result.passed is True

    def test_full_vocab_lesson_passes_all_tags(self):
        sections = _build_vocab_lesson()
        tags = ["concept_map", "film_based", "shy_student_1on1", "active_recall", "why_wrong_reasoning"]  # noqa: E501
        # active_recall requires active_recall_prompt — not in build, so test without it
        tags = ["concept_map", "film_based", "shy_student_1on1", "why_wrong_reasoning"]
        result = check_methodology_compliance(sections, tags)
        assert result.passed is True
        assert result.violations == []

    def test_film_based_tag_satisfied_by_film_clip_activity(self):
        sections = _build_vocab_lesson(include={"film"})
        result = check_methodology_compliance(sections, ["film_based"])
        assert result.passed is True

    def test_film_based_tag_fails_without_film_component(self):
        sections = _build_vocab_lesson(include={"vocab", "questions"})
        result = check_methodology_compliance(sections, ["film_based"])
        assert result.passed is False
        assert len(result.violations) == 1
        assert result.violations[0].tag == "film_based"
        assert "film_clip_activity" in result.violations[0].message

    def test_concept_map_tag_satisfied_by_vocab_cluster(self):
        sections = _build_vocab_lesson(include={"vocab"})
        result = check_methodology_compliance(sections, ["concept_map"])
        assert result.passed is True

    def test_concept_map_tag_satisfied_by_contrastive_pairs(self):
        sections = [{"components": [{"type": "contrastive_pairs", "rows": []}]}]
        result = check_methodology_compliance(sections, ["concept_map"])
        assert result.passed is True

    def test_shy_student_1on1_satisfied_by_roleplay_script(self):
        sections = _build_vocab_lesson(include={"roleplay"})
        result = check_methodology_compliance(sections, ["shy_student_1on1"])
        assert result.passed is True

    def test_shy_student_1on1_fails_without_roleplay(self):
        sections = _build_vocab_lesson(include={"vocab", "film"})
        result = check_methodology_compliance(sections, ["shy_student_1on1"])
        assert result.passed is False
        assert result.violations[0].tag == "shy_student_1on1"

    def test_active_recall_satisfied_by_active_recall_prompt(self):
        sections = [{"components": [
            {"type": "active_recall_prompt", "instruction": "Redraw.", "time_minutes": 3}
        ]}]
        result = check_methodology_compliance(sections, ["active_recall"])
        assert result.passed is True

    def test_active_recall_fails_without_component(self):
        sections = _build_vocab_lesson(include={"vocab"})
        result = check_methodology_compliance(sections, ["active_recall"])
        assert result.passed is False
        assert result.violations[0].tag == "active_recall"

    def test_why_wrong_reasoning_passes_when_all_cards_have_reasons(self):
        sections = _build_vocab_lesson(include={"questions"})
        result = check_methodology_compliance(sections, ["why_wrong_reasoning"])
        assert result.passed is True

    def test_why_wrong_reasoning_fails_when_card_missing_wrong_reasons(self):
        sections = [{"components": [
            {"type": "question_card", "id": 1, "text": "Q?",
             "options": {"A": "a"}, "answer": "A", "explain": "e"}
            # no wrong_reasons
        ]}]
        result = check_methodology_compliance(sections, ["why_wrong_reasoning"])
        assert result.passed is False
        assert result.violations[0].tag == "why_wrong_reasoning"
        assert "wrong_reasons" in result.violations[0].message

    def test_why_wrong_reasoning_passes_vacuously_when_no_questions(self):
        sections = _build_vocab_lesson(include={"vocab"})
        result = check_methodology_compliance(sections, ["why_wrong_reasoning"])
        assert result.passed is True

    def test_multiple_violations_reported(self):
        sections = []  # empty — nothing satisfies anything
        tags = ["film_based", "shy_student_1on1", "active_recall"]
        result = check_methodology_compliance(sections, tags)
        assert result.passed is False
        assert len(result.violations) == 3
        violation_tags = {v.tag for v in result.violations}
        assert violation_tags == {"film_based", "shy_student_1on1", "active_recall"}

    def test_unknown_tag_ignored(self):
        sections = []
        result = check_methodology_compliance(sections, ["timed_quiz", "roleplay_script"])
        assert result.passed is True  # these tags have no structural requirement

    def test_returns_methodology_gate_result_type(self):
        result = check_methodology_compliance([], [])
        assert isinstance(result, MethodologyGateResult)
        assert isinstance(result.violations, list)
