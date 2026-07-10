"""Shared solver-verified question shape for Subject Capability Packs
(#447 Math, #448 Science): every question's correct answer is computed
via `math_solver.solve_arithmetic_expression` -- never trusted as agent
output -- and one wrong option is a documented misconception's actual
computed result, not an arbitrary distractor. Subject-specific modules
(math_question_builder.py, science_question_builder.py) supply the
grade-band expression generators; this module supplies the common
question shape, distractor math, and question_card projection.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from fractions import Fraction

from common.contracts.grade_band import GradeBand
from packages.agents.teaching_pack.subject_packs.math_solver import (
    format_fraction,
    solve_arithmetic_expression,
)


@dataclass(frozen=True, slots=True)
class SolverQuestion:
    id: str
    grade_band: GradeBand
    standard_code: str
    misconception_id: str
    prompt_en: str
    prompt_vi: str
    correct_expression: str
    correct_answer: Fraction
    misconception_expression: str
    misconception_answer: Fraction


def distinct_offset(correct: Fraction, taken: set[Fraction]) -> Fraction:
    offset = Fraction(1)
    while True:
        for candidate in (correct + offset, correct - offset):
            if candidate not in taken:
                return candidate
        offset += 1


def build_solver_question(
    *,
    id_prefix: str,
    index: int,
    grade_band: GradeBand,
    standard_code: str,
    misconception_id: str,
    correct_expr: str,
    misconception_expr: str,
    prompt_en: str,
    prompt_vi: str,
) -> SolverQuestion:
    correct_answer = solve_arithmetic_expression(correct_expr)
    misconception_answer = solve_arithmetic_expression(misconception_expr)
    return SolverQuestion(
        id=f"{id_prefix}-{grade_band.value}-{index + 1}",
        grade_band=grade_band,
        standard_code=standard_code,
        misconception_id=misconception_id,
        prompt_en=prompt_en,
        prompt_vi=prompt_vi,
        correct_expression=correct_expr,
        correct_answer=correct_answer,
        misconception_expression=misconception_expr,
        misconception_answer=misconception_answer,
    )


def to_question_card(question: SolverQuestion, *, locale: str = "vi") -> dict[str, object]:
    """Projects a SolverQuestion into the question_card shape quiz_specialist/
    drill_specialist already emit (id/text/options/answer/explain), so no
    renderer change is needed to display it."""
    prompt = question.prompt_vi if locale == "vi" else question.prompt_en
    correct_text = format_fraction(question.correct_answer)
    taken = {question.correct_answer, question.misconception_answer}
    distractor_a = distinct_offset(question.correct_answer, taken)
    taken.add(distractor_a)
    distractor_b = distinct_offset(question.correct_answer, taken)

    options_by_value = {
        question.correct_answer: correct_text,
        question.misconception_answer: format_fraction(question.misconception_answer),
        distractor_a: format_fraction(distractor_a),
        distractor_b: format_fraction(distractor_b),
    }
    ordered_values = list(options_by_value.keys())
    # Shuffle deterministically (seeded from the question id) so the correct
    # answer isn't always in the same slot -- a real quiz can't let students
    # exploit "the answer is always A".
    random.Random(question.id).shuffle(ordered_values)
    letters = ["A", "B", "C", "D"]
    options = {letter: options_by_value[value] for letter, value in zip(letters, ordered_values, strict=True)}
    answer_letter = next(letter for letter, value in zip(letters, ordered_values, strict=True) if value == question.correct_answer)

    explain = (
        f"Solved deterministically: {question.correct_expression} = {correct_text} "
        f"(standard {question.standard_code}; guards misconception {question.misconception_id})"
        if locale != "vi"
        else (
            f"Đáp án chính xác: {question.correct_expression} = {correct_text} "
            f"(chuẩn {question.standard_code}; tránh ngộ nhận {question.misconception_id})"
        )
    )
    return {
        "type": "question_card",
        "id": question.id,
        "text": prompt,
        "options": options,
        "answer": answer_letter,
        "explain": explain,
        "grade_band": question.grade_band.value,
        "standard_code": question.standard_code,
        "misconception_id": question.misconception_id,
    }
