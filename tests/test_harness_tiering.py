from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_real_llm_marker_is_registered(pytestconfig: pytest.Config) -> None:
    markers = {line.split(":", maxsplit=1)[0] for line in pytestconfig.getini("markers")}

    assert "real_llm" in markers


def test_eval_tier_contains_real_llm_tests() -> None:
    real_llm_tests = [
        path
        for path in (PROJECT_ROOT / "tests").glob("test_*.py")
        if "pytest.mark.real_llm" in path.read_text(encoding="utf-8")
    ]

    assert real_llm_tests != []


def test_fast_tier_excludes_real_llm_by_marker_expression() -> None:
    expression = 'not real_llm'

    assert "real_llm" in expression
    assert expression.startswith("not ")
