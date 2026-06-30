from __future__ import annotations

from typing import Any

from tests.fixtures.inverse_thinking import load_fixture


def english_grammar_pack() -> dict[str, Any]:
    return dict(load_fixture("english_grammar_present_perfect").data["pack"])


def math_misconception_pack() -> dict[str, Any]:
    return dict(load_fixture("math_fraction_denominator_addition").data["pack"])


def science_misconception_pack() -> dict[str, Any]:
    return dict(load_fixture("science_current_consumption_false_model").data["pack"])
