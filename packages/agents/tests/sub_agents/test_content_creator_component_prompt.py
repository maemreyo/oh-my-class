from __future__ import annotations

import pytest

from packages.agents.sub_agents.content_creator.prompt_contract import (
    ACTIVE_ARTIFACT_TYPES,
    build_single_artifact_prompt,
)


def _prompt_for(artifact_type: str) -> str:
    return build_single_artifact_prompt(
        lesson_summary={
            "topic": "Equivalent fractions",
            "learning_objectives": ["Compare equivalent fractions using visual models"],
        },
        research_summary={"key_findings": ["Use area models before symbolic shortcuts"]},
        artifact_type=artifact_type,
        theme="default",
    )


@pytest.mark.parametrize("artifact_type", ACTIVE_ARTIFACT_TYPES)
def test_prompt_requires_component_first_json_for_every_active_artifact_type(artifact_type: str) -> None:
    prompt = _prompt_for(artifact_type)

    assert "Component-first contract" in prompt
    assert "section.components" in prompt
    assert "question_card" in prompt
    assert "question_list" in prompt
    assert "callout" in prompt
    assert "raw HTML" in prompt
    assert "CSS" in prompt
    assert "class names" in prompt
    assert "CDN URLs" in prompt
    assert f"ArtifactContent JSON object of type '{artifact_type}'" in prompt


@pytest.mark.parametrize("artifact_type", ACTIVE_ARTIFACT_TYPES)
def test_prompt_requires_rich_output_not_one_section_shell(artifact_type: str) -> None:
    prompt = _prompt_for(artifact_type)

    assert "one-section shell" in prompt
    assert "multiple" in prompt
    assert "teacher to judge" in prompt


def test_quiz_prompt_requires_answer_key_separation() -> None:
    prompt = _prompt_for("quiz")

    assert "teacher_only" in prompt
    assert "never leak answers" in prompt
    assert "5 question" in prompt


def test_infographic_prompt_bans_external_image_urls() -> None:
    prompt = _prompt_for("infographic")

    assert "external image URLs" in prompt
    assert "stat_grid" in prompt
    assert "concept_map" in prompt
