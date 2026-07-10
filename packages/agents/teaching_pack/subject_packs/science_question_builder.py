"""Real, solver-verified science question generation per Grade Band (#448).

Bridges the Science Subject Capability Pack's declared misconceptions
(common/component_strategy_knowledge/capabilities/science_capability_pack.json)
to actual quiz/drill content, reusing the same solver-verification
architecture #447 established for math (question shape, distractor math,
and question_card projection live in `solver_question_builder.py`):
every question's correct answer is computed by
`math_solver.solve_arithmetic_expression`, and one wrong option is the
documented misconception's actual computed result -- unit conversion and
kinematics/energy arithmetic are as solver-checkable as fraction
arithmetic, so no separate "science solver" was needed.
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
    to_question_card as to_question_card,  # re-exported for callers
)

_STANDARD_CODE_BY_BAND: dict[GradeBand, str] = {
    GradeBand.K_2: "MOET.TNXH.1.DO_DAI_CAN_NANG",
    GradeBand.GRADES_3_5: "MOET.KHOA_HOC.5.DO_LUONG",
    GradeBand.GRADES_6_8: "MOET.KHTN.8.VAN_TOC",
    GradeBand.GRADES_9_12: "MOET.VATLY.10.DONG_NANG",
}

_MISCONCEPTION_ID_BY_BAND: dict[GradeBand, str] = {
    GradeBand.K_2: "k2_combines_pushes_by_multiplying_instead_of_adding",
    GradeBand.GRADES_3_5: "grade35_conversion_factor_error",
    GradeBand.GRADES_6_8: "grade68_average_speed_by_averaging_speeds",
    GradeBand.GRADES_9_12: "grade912_forgets_to_square_velocity",
}


def _k2_question(rng: random.Random, index: int) -> SolverQuestion:
    # Two same-direction pushes combine by addition; the documented
    # misconception multiplies the two strengths instead.
    a = rng.randint(2, 6)
    b = rng.randint(2, 6)
    if a == 2 and b == 2:  # a+b == a*b only at (2, 2): avoid the answer/misconception collision
        b = 3
    correct_expr = f"{a} + {b}"
    misconception_expr = f"{a} * {b}"  # k2_combines_pushes_by_multiplying_instead_of_adding
    prompt_en = f"Push A moves a cart {a} units. Push B (same direction) adds {b} more units. Total units moved?"
    prompt_vi = f"Lực đẩy A làm xe di chuyển {a} đơn vị. Lực đẩy B (cùng hướng) thêm {b} đơn vị. Tổng số đơn vị di chuyển?"
    return build_solver_question(
        id_prefix="science", index=index, grade_band=GradeBand.K_2,
        standard_code=_STANDARD_CODE_BY_BAND[GradeBand.K_2],
        misconception_id=_MISCONCEPTION_ID_BY_BAND[GradeBand.K_2],
        correct_expr=correct_expr, misconception_expr=misconception_expr,
        prompt_en=prompt_en, prompt_vi=prompt_vi,
    )


def _grade35_question(rng: random.Random, index: int) -> SolverQuestion:
    # Metric length conversion: alternate cm->m (divide by 100) and
    # m->cm (multiply by 100) so direction can't be pattern-matched
    # (grade35_bigger_unit_means_bigger_number), and the misconception
    # uses the wrong power of 10 (grade35_conversion_factor_error).
    if index % 2 == 0:
        cm = rng.randint(2, 9) * 100
        correct_expr = f"{cm}/100"
        misconception_expr = f"{cm}/10"
        prompt_en = f"{cm} cm = ? m"
        prompt_vi = f"{cm} cm = ? m"
    else:
        m = rng.randint(2, 9)
        correct_expr = f"{m}*100"
        misconception_expr = f"{m}*10"
        prompt_en = f"{m} m = ? cm"
        prompt_vi = f"{m} m = ? cm"
    return build_solver_question(
        id_prefix="science", index=index, grade_band=GradeBand.GRADES_3_5,
        standard_code=_STANDARD_CODE_BY_BAND[GradeBand.GRADES_3_5],
        misconception_id=_MISCONCEPTION_ID_BY_BAND[GradeBand.GRADES_3_5],
        correct_expr=correct_expr, misconception_expr=misconception_expr,
        prompt_en=prompt_en, prompt_vi=prompt_vi,
    )


def _grade68_question(rng: random.Random, index: int) -> SolverQuestion:
    # Average speed across two equal-distance legs at different speeds:
    # correct = total_distance / total_time; misconception averages the
    # two speeds directly (grade68_average_speed_by_averaging_speeds).
    distance = rng.choice([60, 90, 120])
    speed_1 = rng.choice([20, 30, 40])
    speed_2 = rng.choice([n for n in (20, 30, 40, 60) if n != speed_1])
    correct_expr = f"(2*{distance})/({distance}/{speed_1} + {distance}/{speed_2})"
    misconception_expr = f"({speed_1}+{speed_2})/2"
    prompt_en = (
        f"A trip covers {distance} km at {speed_1} km/h, then another {distance} km at {speed_2} km/h. "
        "What is the average speed for the whole trip (km/h)?"
    )
    prompt_vi = (
        f"Một chuyến đi gồm {distance} km với tốc độ {speed_1} km/h, sau đó {distance} km với tốc độ {speed_2} km/h. "
        "Tốc độ trung bình của cả chuyến đi là bao nhiêu (km/h)?"
    )
    return build_solver_question(
        id_prefix="science", index=index, grade_band=GradeBand.GRADES_6_8,
        standard_code=_STANDARD_CODE_BY_BAND[GradeBand.GRADES_6_8],
        misconception_id=_MISCONCEPTION_ID_BY_BAND[GradeBand.GRADES_6_8],
        correct_expr=correct_expr, misconception_expr=misconception_expr,
        prompt_en=prompt_en, prompt_vi=prompt_vi,
    )


def _grade912_question(rng: random.Random, index: int) -> SolverQuestion:
    # Kinetic energy KE = (1/2) * m * v^2 -- expanded as v*v since the
    # solver grammar has no exponent operator. Misconception forgets to
    # square v (grade912_forgets_to_square_velocity).
    mass = rng.randint(2, 9)
    velocity = rng.randint(2, 9)
    correct_expr = f"(1/2)*{mass}*{velocity}*{velocity}"
    misconception_expr = f"(1/2)*{mass}*{velocity}"
    prompt_en = f"A {mass} kg object moves at {velocity} m/s. What is its kinetic energy (J), KE = (1/2) * m * v^2?"
    prompt_vi = f"Một vật khối lượng {mass} kg chuyển động với vận tốc {velocity} m/s. Động năng (J) là bao nhiêu, biết KE = (1/2) * m * v^2?"
    return build_solver_question(
        id_prefix="science", index=index, grade_band=GradeBand.GRADES_9_12,
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


def build_science_questions(grade_band: GradeBand, *, count: int = 4, seed: int = 0) -> list[SolverQuestion]:
    """Deterministic given the same `seed` -- same grade band + seed always
    produces the same problem set (#448 AC: deterministic and traceable)."""
    rng = random.Random(seed)
    generator = _GENERATORS[grade_band]
    return [generator(rng, index) for index in range(count)]
