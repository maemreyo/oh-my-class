from __future__ import annotations

import pytest

from packages.agents.sub_agents.content_creator.hierarchical import build_hierarchical_artifacts
from packages.agents.teaching_pack.stages import StageEnum


async def test_hierarchical_creator_outlines_then_fills_sections(stub_section_prose) -> None:
    result = await build_hierarchical_artifacts({
        "lesson_plan": _lesson_plan(),
        "research_bundle": _research_bundle(),
        "artifact_types": ["lesson"],
        "theme": "default",
        "run_id": "run-cc-hierarchy",
        "current_step": StageEnum.ARTIFACT_WORKFLOW,
        "artifacts": None,
    })

    artifact = result["artifacts"][0]

    assert artifact["artifact_type"] == "lesson"
    assert artifact["metadata"]["generation_mode"] == "outline_fill_coherence"
    assert [section["section_id"] for section in artifact["sections"]]
    assert all(section["metadata"]["filled_independently"] for section in artifact["sections"])


async def test_hierarchical_creator_marks_failed_section_needs_regen(stub_section_prose) -> None:
    result = await build_hierarchical_artifacts({
        "lesson_plan": _lesson_plan(),
        "research_bundle": _research_bundle(),
        "artifact_types": ["lesson", "quiz"],
        "theme": "default",
        "run_id": "run-cc-resilience",
        "current_step": StageEnum.ARTIFACT_WORKFLOW,
        "artifacts": None,
        "force_section_failures": ["lesson:guided_practice"],
    })

    lesson = result["artifacts"][0]
    quiz = result["artifacts"][1]
    failed = [section for section in lesson["sections"] if section.get("needs_regen")]

    assert failed
    assert quiz["metadata"]["generation_status"] == "complete"
    assert lesson["metadata"]["generation_status"] == "needs_regen"


async def test_hierarchical_creator_enforces_guards_and_verified_facts(stub_section_prose) -> None:
    result = await build_hierarchical_artifacts({
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
        "current_step": StageEnum.ARTIFACT_WORKFLOW,
        "artifacts": None,
    })

    artifact = result["artifacts"][0]
    content = str(artifact)

    assert "Fraction equivalence uses equal value representations" in content
    assert "Fractions always have different values" not in content
    assert artifact["metadata"]["grounding_status"] == "verified_subset"

async def test_hierarchical_creator_fills_selected_vocabulary_strategy_components(stub_section_prose) -> None:
    result = await build_hierarchical_artifacts({
        "lesson_plan": _lesson_plan(),
        "research_bundle": _research_bundle(),
        "artifact_types": ["lesson"],
        "theme": "default",
        "run_id": "run-cc-strategy-vocab",
        "current_step": StageEnum.ARTIFACT_WORKFLOW,
        "artifacts": None,
        "component_strategy_plan": _strategy_plan("lesson", [
            _strategy_slot("slot-vocab", "vocab_cluster", "vocabulary_cluster", ["introduce target terms"]),
            _strategy_slot("slot-contrast", "contrastive_pairs", "contrastive_compare", ["separate confusable terms"]),
        ]),
    })

    artifact = result["artifacts"][0]
    components = _strategy_components(artifact)

    assert [component["type"] for component in components] == ["vocab_cluster", "contrastive_pairs"]
    assert artifact["metadata"]["component_strategy"]["slot_ids"] == ["slot-vocab", "slot-contrast"]
    assert all(component["strategy_slot_id"] in {"slot-vocab", "slot-contrast"} for component in components)

async def test_hierarchical_creator_fills_selected_exam_strategy_components(stub_section_prose) -> None:
    result = await build_hierarchical_artifacts({
        "lesson_plan": _lesson_plan(),
        "research_bundle": _research_bundle(),
        "artifact_types": ["quiz"],
        "theme": "default",
        "run_id": "run-cc-strategy-exam",
        "current_step": StageEnum.ARTIFACT_WORKFLOW,
        "artifacts": None,
        "component_strategy_plan": _strategy_plan("quiz", [
            _strategy_slot("slot-questions", "question_list", "exam_rehearsal", ["include four options"], max_items=2),
        ]),
    })

    artifact = result["artifacts"][0]
    components = _strategy_components(artifact)
    question_list = components[0]

    assert question_list["type"] == "question_list"
    assert question_list["strategy_slot_id"] == "slot-questions"
    questions = question_list["questions"]
    assert isinstance(questions, list)
    assert len(questions) == 2
    assert artifact["metadata"]["component_strategy"]["slot_ids"] == ["slot-questions"]

async def test_hierarchical_creator_fills_selected_concept_strategy_components(stub_section_prose) -> None:
    result = await build_hierarchical_artifacts({
        "lesson_plan": _lesson_plan(),
        "research_bundle": _research_bundle(),
        "artifact_types": ["lesson"],
        "theme": "default",
        "run_id": "run-cc-strategy-concept",
        "current_step": StageEnum.ARTIFACT_WORKFLOW,
        "artifacts": None,
        "component_strategy_plan": _strategy_plan("lesson", [
            _strategy_slot("slot-flow", "flow_step", "concept_model_build", ["show ordered model steps"]),
        ]),
    })

    components = _strategy_components(result["artifacts"][0])

    assert components[0]["type"] == "flow_step"
    assert components[0]["strategy_slot_id"] == "slot-flow"
    assert components[0]["steps"]

async def test_hierarchical_creator_records_typed_fallback_for_unsupported_strategy_component(stub_section_prose) -> None:
    result = await build_hierarchical_artifacts({
        "lesson_plan": _lesson_plan(),
        "research_bundle": _research_bundle(),
        "artifact_types": ["lesson"],
        "theme": "default",
        "run_id": "run-cc-strategy-fallback",
        "current_step": StageEnum.ARTIFACT_WORKFLOW,
        "artifacts": None,
        "component_strategy_plan": _strategy_plan("lesson", [
            _strategy_slot("slot-unsupported", "unsupported_component", "unsupported_move", ["must fallback"]),
        ]),
    })

    artifact = result["artifacts"][0]
    fallback = artifact["metadata"]["component_strategy"]["fallbacks"][0]

    assert fallback == {
        "slot_id": "slot-unsupported",
        "original_move_id": "unsupported_move",
        "attempted_component": "unsupported_component",
        "reason": "unsupported_component_type",
    }
    assert _strategy_components(artifact)[0]["type"] == "callout"

async def test_hierarchical_creator_does_not_silently_downgrade_selected_component_to_prose(stub_section_prose) -> None:
    result = await build_hierarchical_artifacts({
        "lesson_plan": _lesson_plan(),
        "research_bundle": _research_bundle(),
        "artifact_types": ["lesson"],
        "theme": "default",
        "run_id": "run-cc-no-prose-downgrade",
        "current_step": StageEnum.ARTIFACT_WORKFLOW,
        "artifacts": None,
        "component_strategy_plan": _strategy_plan("lesson", [
            _strategy_slot("slot-vocab", "vocab_cluster", "vocabulary_cluster", ["introduce target terms"]),
        ]),
    })

    selected_components = _strategy_components(result["artifacts"][0])

    assert selected_components
    assert all(component["type"] != "paragraph" for component in selected_components)


async def test_hierarchical_creator_preserves_supporting_micro_component_lineage(stub_section_prose) -> None:
    result = await build_hierarchical_artifacts({
        "lesson_plan": _lesson_plan(),
        "research_bundle": _research_bundle(),
        "artifact_types": ["lesson"],
        "theme": "default",
        "run_id": "run-cc-micro-lineage",
        "current_step": StageEnum.ARTIFACT_WORKFLOW,
        "artifacts": None,
        "component_strategy_plan": _strategy_plan("lesson", [
            _strategy_slot("slot-parent", "vocab_cluster", "vocabulary_cluster", ["introduce target terms"]),
            {
                **_strategy_slot("slot-micro", "active_recall_prompt", "retrieval_check", ["quick self-check"]),
                "parent_slot_id": "slot-parent",
            },
        ]),
    })

    components = _strategy_components(result["artifacts"][0])
    micro = next(component for component in components if component["strategy_slot_id"] == "slot-micro")

    assert micro["strategy_parent_slot_id"] == "slot-parent"


async def test_hierarchical_creator_fails_hard_on_missing_methodology_component(stub_section_prose) -> None:
    with pytest.raises(ValueError, match="methodology component"):
        await build_hierarchical_artifacts({
            "lesson_plan": {
                **_lesson_plan(),
                "methodology": {"tags": ["inverse_thinking"]},
            },
            "research_bundle": _research_bundle(),
            "artifact_types": ["lesson"],
            "theme": "default",
            "run_id": "run-cc-methodology",
            "current_step": StageEnum.ARTIFACT_WORKFLOW,
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

def _strategy_components(artifact: dict[str, object]) -> list[dict[str, object]]:
    sections = artifact["sections"]
    assert isinstance(sections, list)
    components: list[dict[str, object]] = []
    for section in sections:
        assert isinstance(section, dict)
        for component in section.get("components", []):
            if isinstance(component, dict) and "strategy_slot_id" in component:
                components.append(component)
    return components

def _strategy_plan(artifact_type: str, slots: list[dict[str, object]]) -> dict[str, object]:
    return {
        "strategy_id": "strategy-run-test",
        "strategy_schema_version": "component_strategy.v1",
        "recommended": {
            "learning_sequence": slots,
            "artifact_strategies": [{
                "artifact_type": artifact_type,
                "ordered_slot_ids": [str(slot["slot_id"]) for slot in slots],
                "notes_for_creator": ["Use typed selected components."],
            }],
        },
    }

def _strategy_slot(
    slot_id: str,
    component_type: str,
    learning_move_id: str,
    fill_requirements: list[str],
    *,
    max_items: int = 3,
) -> dict[str, object]:
    return {
        "slot_id": slot_id,
        "sequence_id": "seq-1",
        "phase": "guided_practice",
        "learning_move_id": learning_move_id,
        "component_type": component_type,
        "component_binding_id": f"{component_type}@1.0.0",
        "objective_refs": [{"objective_id": "LO-1", "objective_revision": "rev-1"}],
        "target_artifacts": ["lesson", "quiz"],
        "fill_requirements": fill_requirements,
        "forbidden_fill_patterns": ["paragraph_only_downgrade"],
        "budget": {
            "ideal_time_minutes": 5,
            "max_time_minutes": 7,
            "ideal_item_count": 1,
            "max_item_count": max_items,
        },
    }
