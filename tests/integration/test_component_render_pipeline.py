from __future__ import annotations

from typing import Any

import pytest

from common.contracts.artifact import ArtifactContent
from packages.agents.nodes.finalize import step_12_finalize
from packages.agents.nodes.state import NodeState
from packages.quality.layer1_schema.component_gate import validate_component_minimums
from packages.quality.layer2_content.component_scorer import score_component_usage


@pytest.fixture
def lesson_with_components() -> dict[str, Any]:
    return {
        "artifact_id": "lesson-components",
        "artifact_type": "lesson",
        "title": "Travel Vocabulary Components",
        "theme": "default",
        "sections": [
            {
                "type": "warmup",
                "title": "Warm-up film activity",
                "components": [
                    {
                        "type": "film_clip_activity",
                        "clips": [
                            {
                                "title": "Airport check-in scene",
                                "description": "Students listen for check-in and boarding vocabulary.",
                            },
                        ],
                        "hunt_chips": ["check in", "boarding pass"],
                        "post_viewing_note": "Name one travel phrase you heard.",
                    },
                ],
            },
            {
                "type": "concept",
                "title": "Vocabulary clusters",
                "components": [
                    {
                        "type": "vocab_cluster",
                        "title": "Airport verbs",
                        "description": "Actions travelers do before departure.",
                        "items": [
                            {
                                "word": "check in",
                                "definition": "register for a flight",
                                "example": "We check in at the airline counter.",
                            },
                            {
                                "word": "board",
                                "definition": "get onto a plane",
                                "example": "Passengers board after the gate opens.",
                            },
                        ],
                    },
                    {
                        "type": "contrastive_pairs",
                        "rows": [
                            {
                                "terms": "fare / ticket",
                                "distinction": "Fare is the price; ticket is the travel document.",
                            },
                        ],
                    },
                ],
            },
            {
                "type": "practice",
                "title": "Why-wrong practice",
                "components": [
                    {
                        "type": "question_card",
                        "id": 1,
                        "text": "What does 'check in' mean at an airport?",
                        "options": {
                            "A": "Criticize someone",
                            "B": "Register for a flight",
                            "C": "Leave the airport",
                            "D": "Buy snacks",
                        },
                        "answer": "B",
                        "explain": "At an airport, check in means register for a flight.",
                        "wrong_reasons": {
                            "A": "This is a different meaning of check on someone.",
                            "C": "Leaving happens after boarding or arrival.",
                            "D": "Buying snacks is unrelated to registration.",
                        },
                        "essence": "Airport action vocabulary depends on context.",
                        "tip": "Check in happens before security and boarding.",
                    },
                ],
            },
        ],
        "metadata": {"subject": "English", "grade_level": "Grade 8"},
        "accessibility": {"language": "vi"},
    }


def test_component_artifact_validates_and_passes_gate(
    lesson_with_components: dict[str, Any],
) -> None:
    artifact = ArtifactContent(**lesson_with_components)

    assert artifact.artifact_type == "lesson"
    assert validate_component_minimums(lesson_with_components) == []


def test_component_artifact_scores_above_flat_baseline(
    lesson_with_components: dict[str, Any],
) -> None:
    lesson_plan = {
        "methodology": {
            "tags": ["vocab", "contrastive_pairs", "film_based", "why_wrong_reasoning"],
        },
    }

    score = score_component_usage(lesson_with_components, lesson_plan=lesson_plan)

    assert score.score > 6.0
    assert score.unique_intents >= 3
    assert score.methodology_bonus > 0


def test_component_artifact_renders_component_markup(
    lesson_with_components: dict[str, Any],
) -> None:
    state = NodeState(
        raw_request="Teach travel vocabulary",
        teacher_id="t-001",
        class_info={"grade": 8, "subject": "English"},
        run_id="component-render-test",
        artifact_types=["lesson"],
        theme="default",
        artifacts=[lesson_with_components],
        export_formats=["html"],
        exported_files=[],
        current_step=11,
        research_policy="basic",
    )

    result = step_12_finalize(state)
    html = result["exported_files"][0]["content"]

    assert "oh-my-class" in html
    assert "concept-box" in html
    assert "Airport verbs" in html
    assert "qcard" in html
    assert "What does 'check in' mean" in html
    assert "http://" not in html
    assert "https://" not in html


def test_flat_lesson_fails_component_gate() -> None:
    artifact: dict[str, Any] = {
        "artifact_type": "lesson",
        "title": "Flat Lesson",
        "sections": [
            {"title": "Intro", "content": "Only prose."},
            {"title": "Practice", "content": "Still only prose."},
        ],
    }

    issues = validate_component_minimums(artifact)

    assert issues
    assert "no typed components" in issues[0]
