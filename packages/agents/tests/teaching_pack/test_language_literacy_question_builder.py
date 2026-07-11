from __future__ import annotations

import pytest

from common.contracts.grade_band import GradeBand
from packages.agents.teaching_pack.subject_packs.language_literacy_question_builder import (
    build_language_literacy_questions,
)
from packages.agents.teaching_pack.subject_packs.fixed_answer_question_builder import to_question_card


@pytest.mark.parametrize("grade_band", list(GradeBand))
@pytest.mark.parametrize("target_language", ["en", "vi"])
def test_build_language_literacy_questions_is_deterministic_for_a_given_seed(
    grade_band: GradeBand, target_language: str,
) -> None:
    first = build_language_literacy_questions(grade_band, count=4, seed=7, target_language=target_language)
    second = build_language_literacy_questions(grade_band, count=4, seed=7, target_language=target_language)
    assert first == second


@pytest.mark.parametrize("grade_band", list(GradeBand))
@pytest.mark.parametrize("target_language", ["en", "vi"])
def test_to_question_card_has_four_distinct_options_with_a_verified_answer(
    grade_band: GradeBand, target_language: str,
) -> None:
    for question in build_language_literacy_questions(grade_band, count=6, seed=3, target_language=target_language):
        card = to_question_card(question, locale="vi")
        options = card["options"]
        assert isinstance(options, dict)
        assert set(options.keys()) == {"A", "B", "C", "D"}
        assert len(set(options.values())) == 4
        assert options[card["answer"]] == question.correct_vi


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_to_question_card_includes_the_misconception_as_a_wrong_option(grade_band: GradeBand) -> None:
    question = build_language_literacy_questions(grade_band, count=1, seed=5, target_language="en")[0]
    card = to_question_card(question, locale="en")
    assert question.misconception_en in card["options"].values()
    wrong_letters = [letter for letter, text in card["options"].items() if text == question.misconception_en]
    assert card["answer"] not in wrong_letters


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_target_language_selects_distinct_content_from_instruction_locale(grade_band: GradeBand) -> None:
    """#449 AC: target_language and instruction_language are separate axes.
    An English-target question and a Vietnamese-target question must differ
    in their taught content (correct answer) even when rendered through the
    very same instruction locale."""
    en_target = build_language_literacy_questions(grade_band, count=1, seed=9, target_language="en")[0]
    vi_target = build_language_literacy_questions(grade_band, count=1, seed=9, target_language="vi")[0]
    assert en_target.correct_en != vi_target.correct_en
    assert en_target.misconception_id != vi_target.misconception_id


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_no_collisions_across_many_seeds(grade_band: GradeBand) -> None:
    for seed in range(20):
        for target_language in ("en", "vi"):
            for question in build_language_literacy_questions(
                grade_band, count=4, seed=seed, target_language=target_language,
            ):
                assert question.correct_en != question.misconception_en
