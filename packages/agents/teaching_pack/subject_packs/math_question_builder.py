"""Real, solver-verified math question generation per Grade Band (#447).

Bridges the Math Subject Capability Pack's declared misconceptions
(common/component_strategy_knowledge/capabilities/math_capability_pack.json)
to actual quiz/drill content: every question's correct answer is computed
by `math_solver.solve_arithmetic_expression` -- never trusted as agent
output -- and one wrong option is the documented misconception's actual
computed result, not an arbitrary distractor.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction

from common.contracts.grade_band import GradeBand
from packages.agents.teaching_pack.subject_packs.math_solver import (
    format_fraction,
    solve_arithmetic_expression,
)

_STANDARD_CODE_BY_BAND: dict[GradeBand, str] = {
    GradeBand.K_2: "MOET.TOAN.1.PHEP_CONG_TRU_10",
    GradeBand.GRADES_3_5: "MOET.TOAN.5.PHAN_SO",
    GradeBand.GRADES_6_8: "MOET.TOAN.7.SO_HUU_TI",
    GradeBand.GRADES_9_12: "MOET.TOAN.10.PHUONG_TRINH_BAC_NHAT",
}

_MISCONCEPTION_ID_BY_BAND: dict[GradeBand, str] = {
    GradeBand.K_2: "k2_subtraction_order_confusion",
    GradeBand.GRADES_3_5: "grade35_add_numerators_and_denominators",
    GradeBand.GRADES_6_8: "grade68_negative_distribution_sign_error",
    GradeBand.GRADES_9_12: "grade912_order_of_operations_error",
}


@dataclass(frozen=True, slots=True)
class MathQuestion:
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


def _distinct_offsets(correct: Fraction, taken: set[Fraction]) -> Fraction:
    offset = Fraction(1)
    while True:
        for candidate in (correct + offset, correct - offset):
            if candidate not in taken:
                return candidate
        offset += 1


def _k2_question(rng: random.Random, index: int) -> MathQuestion:
    # Always subtraction: it's the one K-2 operation with a genuine
    # numeric misconception-guard (order confusion). Alternates
    # unknown-on-right vs unknown-on-left framing to also guard
    # k2_equals_means_answer_follows, without inventing an unrelated
    # distractor for addition items.
    a = rng.randint(2, 9)
    b = rng.randint(1, a - 1)  # b < a strictly: avoids a-b==0 colliding with the flipped misconception answer
    correct_expr = f"{a} - {b}"
    misconception_expr = f"{b} - {a}"  # flips minuend/subtrahend: k2_subtraction_order_confusion
    if index % 2 == 0:
        prompt_en = f"{a} - {b} = ?"
        prompt_vi = f"{a} - {b} = ?"
    else:
        prompt_en = f"? = {a} - {b}"
        prompt_vi = f"? = {a} - {b}"
    return _build_question(
        rng, index, GradeBand.K_2, correct_expr, misconception_expr, prompt_en, prompt_vi,
    )


def _grade35_question(rng: random.Random, index: int) -> MathQuestion:
    b = rng.choice([2, 3, 4, 5])
    d = rng.choice([n for n in (2, 3, 4, 5) if n != b])
    a = rng.randint(1, b - 1)
    c = rng.randint(1, d - 1)
    correct_expr = f"{a}/{b} + {c}/{d}"
    misconception_expr = f"({a}+{c})/({b}+{d})"  # grade35_add_numerators_and_denominators
    prompt_en = f"{a}/{b} + {c}/{d} = ?"
    prompt_vi = f"{a}/{b} + {c}/{d} = ?"
    return _build_question(
        rng, index, GradeBand.GRADES_3_5, correct_expr, misconception_expr, prompt_en, prompt_vi,
    )


def _grade68_question(rng: random.Random, index: int) -> MathQuestion:
    a = rng.randint(2, 9)
    b = rng.randint(1, 9)
    correct_expr = f"-({a}-{b})"
    misconception_expr = f"-{a}-{b}"  # grade68_negative_distribution_sign_error
    prompt_en = f"-({a} - {b}) = ?"
    prompt_vi = f"-({a} - {b}) = ?"
    return _build_question(
        rng, index, GradeBand.GRADES_6_8, correct_expr, misconception_expr, prompt_en, prompt_vi,
    )


def _grade912_question(rng: random.Random, index: int) -> MathQuestion:
    a = rng.randint(2, 9)
    b = rng.randint(2, 9)
    c = rng.randint(2, 9)
    correct_expr = f"{a} + {b} * {c}"
    misconception_expr = f"({a} + {b}) * {c}"  # grade912_order_of_operations_error
    prompt_en = f"{a} + {b} * {c} = ?"
    prompt_vi = f"{a} + {b} * {c} = ?"
    return _build_question(
        rng, index, GradeBand.GRADES_9_12, correct_expr, misconception_expr, prompt_en, prompt_vi,
    )


def _build_question(
    rng: random.Random,
    index: int,
    grade_band: GradeBand,
    correct_expr: str,
    misconception_expr: str,
    prompt_en: str,
    prompt_vi: str,
) -> MathQuestion:
    correct_answer = solve_arithmetic_expression(correct_expr)
    misconception_answer = solve_arithmetic_expression(misconception_expr)
    return MathQuestion(
        id=f"math-{grade_band.value}-{index + 1}",
        grade_band=grade_band,
        standard_code=_STANDARD_CODE_BY_BAND[grade_band],
        misconception_id=_MISCONCEPTION_ID_BY_BAND[grade_band],
        prompt_en=prompt_en,
        prompt_vi=prompt_vi,
        correct_expression=correct_expr,
        correct_answer=correct_answer,
        misconception_expression=misconception_expr,
        misconception_answer=misconception_answer,
    )


_GENERATORS: dict[GradeBand, Callable[[random.Random, int], MathQuestion]] = {
    GradeBand.K_2: _k2_question,
    GradeBand.GRADES_3_5: _grade35_question,
    GradeBand.GRADES_6_8: _grade68_question,
    GradeBand.GRADES_9_12: _grade912_question,
}


def build_math_questions(grade_band: GradeBand, *, count: int = 4, seed: int = 0) -> list[MathQuestion]:
    """Deterministic given the same `seed` -- same grade band + seed always
    produces the same problem set, which is what "deterministic and
    traceable" (#447 AC) requires for reproducible evidence."""
    rng = random.Random(seed)
    generator = _GENERATORS[grade_band]
    return [generator(rng, index) for index in range(count)]


def to_question_card(question: MathQuestion, *, locale: str = "vi") -> dict[str, object]:
    """Projects a MathQuestion into the question_card shape quiz_specialist/
    drill_specialist already emit (id/text/options/answer/explain), so no
    renderer change is needed to display it."""
    prompt = question.prompt_vi if locale == "vi" else question.prompt_en
    correct_text = format_fraction(question.correct_answer)
    taken = {question.correct_answer, question.misconception_answer}
    distractor_a = _distinct_offsets(question.correct_answer, taken)
    taken.add(distractor_a)
    distractor_b = _distinct_offsets(question.correct_answer, taken)

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
        f"(MOET/CCSS standard {question.standard_code}; guards misconception {question.misconception_id})"
        if locale != "vi"
        else (
            f"Đáp án chính xác: {question.correct_expression} = {correct_text} "
            f"(chuẩn MOET/CCSS {question.standard_code}; tránh ngộ nhận {question.misconception_id})"
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
