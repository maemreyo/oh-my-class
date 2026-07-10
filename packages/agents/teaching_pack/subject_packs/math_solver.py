"""Deterministic arithmetic solver for the Math Subject Capability Pack (#447).

Evaluates a restricted arithmetic grammar (+, -, *, /, parentheses, unary
minus, integer and fraction literals) via `ast`, never `eval` -- the input
is agent/teacher-authored expression text, a real (if narrow) trust
boundary. Every math quiz/drill answer this pack generates is checked
against this solver rather than trusted as agent output, per ADR-054's
"numerical recomputation where supported."
"""

from __future__ import annotations

import ast
import operator
from fractions import Fraction

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class UnsupportedExpressionError(ValueError):
    """Raised for any expression node outside the restricted arithmetic grammar."""


def solve_arithmetic_expression(expression: str) -> Fraction:
    """Evaluate a restricted arithmetic expression to an exact `Fraction`.

    Supports integers, `a/b` fraction literals, `+ - * /`, parentheses, and
    unary +/-. Raises `UnsupportedExpressionError` for anything else
    (names, calls, comparisons, etc.) and `ZeroDivisionError` for division
    by zero -- both fail closed rather than guessing.
    """
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise UnsupportedExpressionError(f"could not parse expression: {expression!r}") from exc
    return _eval_node(tree.body)


def _eval_node(node: ast.expr) -> Fraction:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, int | float):
            raise UnsupportedExpressionError(f"unsupported literal: {node.value!r}")
        return Fraction(node.value).limit_denominator(10_000)
    if isinstance(node, ast.BinOp):
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise UnsupportedExpressionError(f"unsupported operator: {ast.dump(node.op)}")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if op is operator.truediv and right == 0:
            raise ZeroDivisionError(f"division by zero in expression: {ast.dump(node)}")
        return op(left, right)
    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise UnsupportedExpressionError(f"unsupported unary operator: {ast.dump(node.op)}")
        return op(_eval_node(node.operand))
    raise UnsupportedExpressionError(f"unsupported expression node: {ast.dump(node)}")


def format_fraction(value: Fraction) -> str:
    """Renders a whole number without a denominator, otherwise `a/b`."""
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"
