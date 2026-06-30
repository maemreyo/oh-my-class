from __future__ import annotations

from packages.quality.layer2_content.pedagogical import check_pedagogical_metrics


def test_compliant_content_passes_measured_pedagogical_proxies() -> None:
    result = check_pedagogical_metrics(_compliant_content(), lesson_plan=_lesson_plan())

    assert result.passed is True
    assert result.metrics["prompt_alignment"] == "passed"
    assert result.metrics["bloom_coverage"] == "passed"
    assert result.metrics["cognitive_load"] == "passed"
    assert result.metrics["readability_level"] == "passed"
    assert result.metrics["misconception_coverage"] == "passed"


def test_content_unaligned_to_objectives_is_flagged() -> None:
    content = {"title": "Weather", "sections": [{"heading": "Weather", "content": "Clouds rain wind."}]}

    result = check_pedagogical_metrics(content, lesson_plan=_lesson_plan())

    assert result.passed is False
    assert result.metrics["prompt_alignment"] == "failed"


def test_content_missing_bloom_coverage_is_flagged() -> None:
    content = _compliant_content() | {"sections": [{"heading": "Remember", "content": "remember fractions"}]}

    result = check_pedagogical_metrics(content, lesson_plan=_lesson_plan())

    assert result.passed is False
    assert result.metrics["bloom_coverage"] == "failed"


def test_content_above_readability_level_is_flagged() -> None:
    content = _compliant_content() | {
        "sections": [{
            "heading": "Fractions",
            "content": (
                "Fractions require conceptualization of proportional equivalence. "
                "Students analyze numerators and denominators while synthesizing representations."
            ),
        }]
    }

    result = check_pedagogical_metrics(content, lesson_plan=_lesson_plan(grade_level="Grade 1"))

    assert result.passed is False
    assert result.metrics["readability_level"] == "failed"


def test_too_many_new_knowledge_components_is_flagged() -> None:
    content = _compliant_content() | {
        "sections": [{
            "components": [
                {"type": "concept_card", "kc_id": f"kc-{index}"}
                for index in range(5)
            ]
        }]
    }

    result = check_pedagogical_metrics(content, lesson_plan=_lesson_plan())

    assert result.passed is False
    assert result.metrics["cognitive_load"] == "failed"


def test_question_without_wrong_reasons_flags_misconception_coverage() -> None:
    content = _compliant_content() | {
        "sections": [{
            "components": [{
                "type": "question_card",
                "id": "q1",
                "text": "Which fraction equals one half?",
                "bloom_level": "apply",
            }]
        }]
    }

    result = check_pedagogical_metrics(content, lesson_plan=_lesson_plan())

    assert result.passed is False
    assert result.metrics["misconception_coverage"] == "failed"


def _lesson_plan(grade_level: str = "Grade 6") -> dict[str, object]:
    return {
        "grade_level": grade_level,
        "learning_objectives": [
            {"description": "Students understand fractions", "bloom_level": "understand"},
            {"description": "Students apply fractions", "bloom_level": "apply"},
        ],
    }


def _compliant_content() -> dict[str, object]:
    return {
        "title": "Fractions",
        "sections": [{
            "heading": "Fractions practice",
            "content": "We understand fractions. We apply fractions. Half is one of two parts.",
            "components": [{
                "type": "question_card",
                "id": "q1",
                "text": "Which fraction equals one half?",
                "bloom_level": "apply",
                "kc_id": "fractions",
                "wrong_reasons": {"A": "Confuses numerator and denominator."},
            }],
        }],
    }
