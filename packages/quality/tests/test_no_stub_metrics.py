from __future__ import annotations

import ast
from pathlib import Path

from packages.quality.layer2_content import pedagogical
from packages.quality.layer2_content.pedagogical import check_pedagogical_metrics


def test_pedagogical_metrics_do_not_return_unconditional_true_map() -> None:
    source = Path(pedagogical.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    dict_comprehensions = [node for node in ast.walk(tree) if isinstance(node, ast.DictComp)]

    assert all(not isinstance(node.value, ast.Constant) or node.value.value is not True for node in dict_comprehensions)


def test_unmeasured_metrics_are_excluded_from_pass_criteria_and_reported() -> None:
    result = check_pedagogical_metrics({"sections": []}, lesson_plan=None)

    assert result.passed is True
    assert result.metrics["factual_correctness"] == "unmeasured"
    assert result.metrics["solution_accuracy"] == "unmeasured"
    assert result.measured["factual_correctness"] is False
    assert result.measured["solution_accuracy"] is False


def test_measured_failure_controls_pass_criteria() -> None:
    result = check_pedagogical_metrics(
        {"sections": [{"content": "Unrelated weather text."}]},
        lesson_plan={
            "grade_level": "Grade 5",
            "learning_objectives": [
                {"description": "Students understand fractions", "bloom_level": "understand"},
                {"description": "Students apply fractions", "bloom_level": "apply"},
            ],
        },
    )

    assert result.passed is False
    assert result.metrics["prompt_alignment"] == "failed"
