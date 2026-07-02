from __future__ import annotations

import pytest

from packages.agents.sub_agents.content_creator.hierarchical import build_hierarchical_artifacts


def test_hierarchical_creator_outlines_then_fills_sections() -> None:
    result = build_hierarchical_artifacts({
        "lesson_plan": _lesson_plan(),
        "research_bundle": _research_bundle(),
        "artifact_types": ["lesson"],
        "theme": "default",
        "run_id": "run-cc-hierarchy",
        "current_step": 8,
        "artifacts": None,
    })

    artifact = result["artifacts"][0]

    assert artifact["artifact_type"] == "lesson"
    assert artifact["metadata"]["generation_mode"] == "outline_fill_coherence"
    assert [section["section_id"] for section in artifact["sections"]]
    assert all(section["metadata"]["filled_independently"] for section in artifact["sections"])


def test_hierarchical_creator_marks_failed_section_needs_regen() -> None:
    result = build_hierarchical_artifacts({
        "lesson_plan": _lesson_plan(),
        "research_bundle": _research_bundle(),
        "artifact_types": ["lesson", "quiz"],
        "theme": "default",
        "run_id": "run-cc-resilience",
        "current_step": 8,
        "artifacts": None,
        "force_section_failures": ["lesson:guided_practice"],
    })

    lesson = result["artifacts"][0]
    quiz = result["artifacts"][1]
    failed = [section for section in lesson["sections"] if section.get("needs_regen")]

    assert failed
    assert quiz["metadata"]["generation_status"] == "complete"
    assert lesson["metadata"]["generation_status"] == "needs_regen"


def test_hierarchical_creator_enforces_guards_and_verified_facts() -> None:
    result = build_hierarchical_artifacts({
        "lesson_plan": _lesson_plan(),
        "research_bundle": {
            "topic": "Fractions",
            "key_findings": ["Fraction equivalence uses equal value representations"],
            "sources": [{"title": "Source", "verification_status": "VERIFIED"}],
            "contradicted_facts": ["Fractions always have different values"],
        },
        "artifact_types": ["lesson"],
        "theme": "default",
        "run_id": "run-cc-grounding",
        "current_step": 8,
        "artifacts": None,
    })

    artifact = result["artifacts"][0]
    content = str(artifact)

    assert "Fraction equivalence uses equal value representations" in content
    assert "Fractions always have different values" not in content
    assert artifact["metadata"]["grounding_status"] == "verified_subset"


def test_hierarchical_creator_fails_hard_on_missing_methodology_component() -> None:
    with pytest.raises(ValueError, match="methodology component"):
        build_hierarchical_artifacts({
            "lesson_plan": {
                **_lesson_plan(),
                "methodology": {"tags": ["inverse_thinking"]},
            },
            "research_bundle": _research_bundle(),
            "artifact_types": ["lesson"],
            "theme": "default",
            "run_id": "run-cc-methodology",
            "current_step": 8,
            "artifacts": None,
            "disable_methodology_components": True,
        })


def _lesson_plan() -> dict[str, object]:
    return {
        "topic": "Fractions",
        "grade_level": "Grade 5",
        "subject": "math",
        "duration_minutes": 45,
        "learning_objectives": [
            {"description": "Explain equivalent fractions", "bloom_level": "understand"},
            {"description": "Apply equivalent fractions", "bloom_level": "apply"},
        ],
        "learning_plan": {
            "gain_attention": "Hook",
            "inform_objectives": "Objectives",
            "recall_prior": "Recall",
            "present_content": "Content",
            "provide_guidance": "Guidance",
            "elicit_performance": "Practice",
            "provide_feedback": "Feedback",
            "assess_performance": "Assessment",
            "enhance_retention": "Retention",
        },
        "assessment_checkpoints": [
            {"type": "exit_ticket", "description": "Assess equivalent fractions"},
        ],
        "methodology": {"tags": ["active_recall"]},
    }


def _research_bundle() -> dict[str, object]:
    return {
        "topic": "Fractions",
        "key_findings": ["Fraction equivalence uses equal value representations"],
        "sources": [{"title": "Source", "verification_status": "VERIFIED"}],
    }
