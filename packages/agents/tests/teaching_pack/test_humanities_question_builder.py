from __future__ import annotations

import pytest

from common.contracts.grade_band import GradeBand
from packages.agents.teaching_pack.subject_packs.humanities_question_builder import build_humanities_questions
from packages.agents.teaching_pack.subject_packs.fixed_answer_question_builder import to_question_card


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_build_humanities_questions_is_deterministic_for_a_given_seed(grade_band: GradeBand) -> None:
    first = build_humanities_questions(grade_band, count=4, seed=7)
    second = build_humanities_questions(grade_band, count=4, seed=7)
    assert first == second


@pytest.mark.parametrize("grade_band", list(GradeBand))
@pytest.mark.parametrize("locale", ["en", "vi"])
def test_to_question_card_has_four_distinct_options_with_a_verified_answer(
    grade_band: GradeBand, locale: str,
) -> None:
    for question in build_humanities_questions(grade_band, count=6, seed=3):
        card = to_question_card(question, locale=locale)
        options = card["options"]
        assert isinstance(options, dict)
        assert set(options.keys()) == {"A", "B", "C", "D"}
        assert len(set(options.values())) == 4
        expected = question.correct_vi if locale == "vi" else question.correct_en
        assert options[card["answer"]] == expected


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_to_question_card_includes_the_misconception_as_a_wrong_option(grade_band: GradeBand) -> None:
    question = build_humanities_questions(grade_band, count=1, seed=5)[0]
    card = to_question_card(question, locale="en")
    assert question.misconception_en in card["options"].values()
    wrong_letters = [letter for letter, text in card["options"].items() if text == question.misconception_en]
    assert card["answer"] not in wrong_letters


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_no_collisions_across_many_seeds(grade_band: GradeBand) -> None:
    for seed in range(20):
        for question in build_humanities_questions(grade_band, count=4, seed=seed):
            assert question.correct_en != question.misconception_en
            assert question.correct_vi != question.misconception_vi
