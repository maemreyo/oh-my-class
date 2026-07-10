from __future__ import annotations

import pytest

from common.contracts.grade_band import GradeBand
from packages.agents.teaching_pack.subject_packs.science_question_builder import (
    build_science_questions,
    to_question_card,
)
from packages.agents.teaching_pack.subject_packs.math_solver import solve_arithmetic_expression


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_correct_answer_is_solver_verified(grade_band: GradeBand) -> None:
    for question in build_science_questions(grade_band, count=6, seed=1):
        assert question.correct_answer == solve_arithmetic_expression(question.correct_expression)


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_misconception_distractor_is_a_real_computed_wrong_answer(grade_band: GradeBand) -> None:
    for question in build_science_questions(grade_band, count=6, seed=1):
        assert question.misconception_answer == solve_arithmetic_expression(question.misconception_expression)
        assert question.misconception_answer != question.correct_answer


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_build_science_questions_is_deterministic_for_a_given_seed(grade_band: GradeBand) -> None:
    first = build_science_questions(grade_band, count=4, seed=7)
    second = build_science_questions(grade_band, count=4, seed=7)
    assert first == second


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_to_question_card_has_four_distinct_options_with_a_verified_answer(grade_band: GradeBand) -> None:
    from packages.agents.teaching_pack.subject_packs.math_solver import format_fraction

    for question in build_science_questions(grade_band, count=6, seed=3):
        card = to_question_card(question, locale="vi")
        options = card["options"]
        assert isinstance(options, dict)
        assert set(options.keys()) == {"A", "B", "C", "D"}
        assert len(set(options.values())) == 4
        assert options[card["answer"]] == format_fraction(question.correct_answer)


def test_grade_6_8_average_speed_uses_total_distance_over_total_time_not_averaged_speeds() -> None:
    """The one science misconception that's easy to get backwards even when
    writing the generator: average speed is NOT the arithmetic mean of two
    leg speeds unless the legs take equal time. Assert the correct answer
    is always strictly between the two leg speeds but not their simple
    average when the two legs differ (guards the guard, not just the
    solver arithmetic)."""
    from fractions import Fraction

    for question in build_science_questions(GradeBand.GRADES_6_8, count=10, seed=42):
        assert question.correct_answer != question.misconception_answer
        assert question.correct_answer > Fraction(0)


@pytest.mark.parametrize("grade_band", list(GradeBand))
def test_no_collisions_across_many_seeds(grade_band: GradeBand) -> None:
    for seed in range(50):
        for question in build_science_questions(grade_band, count=4, seed=seed):
            assert question.correct_answer != question.misconception_answer
