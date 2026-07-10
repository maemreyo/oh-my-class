from __future__ import annotations

from fractions import Fraction

import pytest

from common.contracts.grade_band import GradeBand
from packages.agents.teaching_pack.subject_packs.math_question_builder import (
    build_math_questions,
    to_question_card,
)
from packages.agents.teaching_pack.subject_packs.math_solver import solve_arithmetic_expression


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_correct_answer_is_solver_verified(grade_band: GradeBand) -> None:
    for question in build_math_questions(grade_band, count=6, seed=1):
        assert question.correct_answer == solve_arithmetic_expression(question.correct_expression)


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_misconception_distractor_is_a_real_computed_wrong_answer(grade_band: GradeBand) -> None:
    for question in build_math_questions(grade_band, count=6, seed=1):
        assert question.misconception_answer == solve_arithmetic_expression(question.misconception_expression)
        assert question.misconception_answer != question.correct_answer


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_build_math_questions_is_deterministic_for_a_given_seed(grade_band: GradeBand) -> None:
    first = build_math_questions(grade_band, count=4, seed=7)
    second = build_math_questions(grade_band, count=4, seed=7)
    assert first == second


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_to_question_card_has_four_distinct_options_with_a_verified_answer(grade_band: GradeBand) -> None:
    for question in build_math_questions(grade_band, count=6, seed=3):
        card = to_question_card(question, locale="vi")
        options = card["options"]
        assert isinstance(options, dict)
        assert set(options.keys()) == {"A", "B", "C", "D"}
        assert len(set(options.values())) == 4
        assert options[card["answer"]] is not None
        from packages.agents.teaching_pack.subject_packs.math_solver import format_fraction
        assert options[card["answer"]] == format_fraction(question.correct_answer)


def test_to_question_card_includes_the_misconception_as_a_wrong_option() -> None:
    from packages.agents.teaching_pack.subject_packs.math_solver import format_fraction
    question = build_math_questions(GradeBand.GRADES_3_5, count=1, seed=5)[0]
    card = to_question_card(question, locale="en")
    misconception_text = format_fraction(question.misconception_answer)
    assert misconception_text in card["options"].values()
    wrong_letters = [letter for letter, text in card["options"].items() if text == misconception_text]
    assert card["answer"] not in wrong_letters


def test_k2_subtraction_never_goes_negative_for_the_correct_answer() -> None:
    for question in build_math_questions(GradeBand.K_2, count=20, seed=11):
        assert question.correct_answer >= Fraction(0)
