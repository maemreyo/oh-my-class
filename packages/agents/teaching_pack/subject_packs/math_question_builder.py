"""Real, solver-verified math question generation per Grade Band (#447).

Bridges the Math Subject Capability Pack's declared misconceptions
(common/component_strategy_knowledge/capabilities/math_capability_pack.json)
to actual quiz/drill content. Question shape, distractor math, and
question_card projection live in `solver_question_builder.py` (shared
with #448 Science); this module supplies the math-specific grade-band
expression generators.
"""

from __future__ import annotations

import random
from collections.abc import Callable

from common.contracts.grade_band import GradeBand
from packages.agents.teaching_pack.subject_packs.solver_question_builder import (
    SolverQuestion,
    build_solver_question,
)
from packages.agents.teaching_pack.subject_packs.solver_question_builder import (
    to_question_card as to_question_card,  # re-exported for existing importers
)

MathQuestion = SolverQuestion

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


def _k2_question(rng: random.Random, index: int) -> SolverQuestion:
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
    return build_solver_question(
        id_prefix="math", index=index, grade_band=GradeBand.K_2,
        standard_code=_STANDARD_CODE_BY_BAND[GradeBand.K_2],
        misconception_id=_MISCONCEPTION_ID_BY_BAND[GradeBand.K_2],
        correct_expr=correct_expr, misconception_expr=misconception_expr,
        prompt_en=prompt_en, prompt_vi=prompt_vi,
    )


def _grade35_question(rng: random.Random, index: int) -> SolverQuestion:
    b = rng.choice([2, 3, 4, 5])
    d = rng.choice([n for n in (2, 3, 4, 5) if n != b])
    a = rng.randint(1, b - 1)
    c = rng.randint(1, d - 1)
    correct_expr = f"{a}/{b} + {c}/{d}"
    misconception_expr = f"({a}+{c})/({b}+{d})"  # grade35_add_numerators_and_denominators
    prompt_en = f"{a}/{b} + {c}/{d} = ?"
    prompt_vi = f"{a}/{b} + {c}/{d} = ?"
    return build_solver_question(
        id_prefix="math", index=index, grade_band=GradeBand.GRADES_3_5,
        standard_code=_STANDARD_CODE_BY_BAND[GradeBand.GRADES_3_5],
        misconception_id=_MISCONCEPTION_ID_BY_BAND[GradeBand.GRADES_3_5],
        correct_expr=correct_expr, misconception_expr=misconception_expr,
        prompt_en=prompt_en, prompt_vi=prompt_vi,
    )


def _grade68_question(rng: random.Random, index: int) -> SolverQuestion:
    a = rng.randint(2, 9)
    b = rng.randint(1, 9)
    correct_expr = f"-({a}-{b})"
    misconception_expr = f"-{a}-{b}"  # grade68_negative_distribution_sign_error
    prompt_en = f"-({a} - {b}) = ?"
    prompt_vi = f"-({a} - {b}) = ?"
    return build_solver_question(
        id_prefix="math", index=index, grade_band=GradeBand.GRADES_6_8,
        standard_code=_STANDARD_CODE_BY_BAND[GradeBand.GRADES_6_8],
        misconception_id=_MISCONCEPTION_ID_BY_BAND[GradeBand.GRADES_6_8],
        correct_expr=correct_expr, misconception_expr=misconception_expr,
        prompt_en=prompt_en, prompt_vi=prompt_vi,
    )


def _grade912_question(rng: random.Random, index: int) -> SolverQuestion:
    a = rng.randint(2, 9)
    b = rng.randint(2, 9)
    c = rng.randint(2, 9)
    correct_expr = f"{a} + {b} * {c}"
    misconception_expr = f"({a} + {b}) * {c}"  # grade912_order_of_operations_error
    prompt_en = f"{a} + {b} * {c} = ?"
    prompt_vi = f"{a} + {b} * {c} = ?"
    return build_solver_question(
        id_prefix="math", index=index, grade_band=GradeBand.GRADES_9_12,
        standard_code=_STANDARD_CODE_BY_BAND[GradeBand.GRADES_9_12],
        misconception_id=_MISCONCEPTION_ID_BY_BAND[GradeBand.GRADES_9_12],
        correct_expr=correct_expr, misconception_expr=misconception_expr,
        prompt_en=prompt_en, prompt_vi=prompt_vi,
    )


_GENERATORS: dict[GradeBand, Callable[[random.Random, int], SolverQuestion]] = {
    GradeBand.K_2: _k2_question,
    GradeBand.GRADES_3_5: _grade35_question,
    GradeBand.GRADES_6_8: _grade68_question,
    GradeBand.GRADES_9_12: _grade912_question,
}


def build_math_questions(
    grade_band: GradeBand, *, count: int = 4, seed: int = 0, target_language: str = "en",
) -> list[SolverQuestion]:
    """Deterministic given the same `seed` -- same grade band + seed always
    produces the same problem set, which is what "deterministic and
    traceable" (#447 AC) requires for reproducible evidence.

    `target_language` is accepted for signature parity with subject builders
    that need it (#449 Language and Literacy) -- arithmetic has no
    target-language axis, so it's unused here."""
    del target_language
    rng = random.Random(seed)
    generator = _GENERATORS[grade_band]
    return [generator(rng, index) for index in range(count)]
