from __future__ import annotations

from fractions import Fraction

import pytest

from packages.agents.teaching_pack.subject_packs.math_solver import (
    UnsupportedExpressionError,
    format_fraction,
    solve_arithmetic_expression,
)


@pytest.mark.parametrize(("expression", "expected"), [
    ("2 + 2", Fraction(4)),
    ("10 - 3", Fraction(7)),
    ("6 * 7", Fraction(42)),
    ("1/2 + 1/2", Fraction(1)),
    ("1/2 + 1/4", Fraction(3, 4)),
    ("3/4 * 2/3", Fraction(1, 2)),
    ("-5 + 2", Fraction(-3)),
    ("(2 + 3) * 4", Fraction(20)),
])
def test_solve_arithmetic_expression_is_exact(expression: str, expected: Fraction) -> None:
    assert solve_arithmetic_expression(expression) == expected


def test_division_by_zero_fails_closed() -> None:
    with pytest.raises(ZeroDivisionError):
        solve_arithmetic_expression("1/0")


@pytest.mark.parametrize("expression", ["__import__('os')", "open('x')", "a + 1", "1 == 1"])
def test_unsupported_expressions_are_rejected_not_evaluated(expression: str) -> None:
    with pytest.raises(UnsupportedExpressionError):
        solve_arithmetic_expression(expression)


@pytest.mark.parametrize(("value", "expected"), [
    (Fraction(4), "4"),
    (Fraction(3, 4), "3/4"),
    (Fraction(-1, 2), "-1/2"),
])
def test_format_fraction(value: Fraction, expected: str) -> None:
    assert format_fraction(value) == expected
