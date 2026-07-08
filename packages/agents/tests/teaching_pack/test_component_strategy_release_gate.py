from __future__ import annotations

from pathlib import Path

from common.contracts.component_strategy import ComponentStrategyRequest
from common.contracts.component_strategy_selector import plan_component_strategy
from packages.agents.sub_agents.content_creator.hierarchical import build_hierarchical_artifacts
from packages.agents.teaching_pack.nodes import TeachingPackState, make_stage_node, route_after_teacher_approval
from packages.agents.teaching_pack.stages import StageEnum, TeachingPackStage, teaching_pack_stages

PROJECT_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_DIR = PROJECT_ROOT / ".scratch" / "component-strategist" / "fixtures"


def test_feature_flagged_path_inserts_strategy_before_research_and_approval() -> None:
    path = tuple(stage.value for stage in teaching_pack_stages(component_strategy_enabled=True))

    assert path[path.index("planning_blueprint") + 1] == "provisional_component_strategy"
    assert path[path.index("post_blueprint_research") + 1] == "finalize_component_strategy"
    assert path[path.index("finalize_component_strategy") + 1] == "teacher_approval"


async def test_strategy_plan_reaches_artifact_workflow_selected_components(stub_section_prose) -> None:
    request = _request("cs08_vocabulary_language_request.json")
    result = plan_component_strategy(request)
    assert result.plan is not None

    artifacts = (await build_hierarchical_artifacts({
        "lesson_plan": _lesson_plan(),
        "research_bundle": _research_bundle(),
        "artifact_types": ["lesson"],
        "theme": "default",
        "run_id": "cs08-flow",
        "current_step": StageEnum.ARTIFACT_WORKFLOW,
        "artifacts": None,
        "component_strategy_plan": result.plan.model_dump(mode="json"),
    }))["artifacts"]

    selected = _strategy_components(artifacts[0])
    assert [component["type"] for component in selected] == ["contrastive_pairs", "vocab_cluster"]


async def test_final_strategy_stage_creates_blueprint_payload_then_routes_to_artifacts(monkeypatch) -> None:
    from packages.agents.config.features import reset_features

    monkeypatch.setenv("FEATURE_COMPONENT_STRATEGIST_V1", "true")
    reset_features()
    stage_node = make_stage_node(TeachingPackStage.FINALIZE_COMPONENT_STRATEGY)
    result = await stage_node(TeachingPackState(
        run_id="cs08-stage-flow",
        contract={
            "teacher_id_hash": "teacher-hash",
            "topic": "Vocabulary boundaries",
            "grade_band": "Grade 5",
            "subject": "language",
            "duration_minutes": 45,
            "export_formats": ["html"],
        },
        artifact_types=["lesson"],
        lesson_plan=_lesson_plan(subject="language"),
        research_brief={
            "factual_risk": "low",
            "source_confidence": "high",
            "prerequisite_risk": "met",
            "evidence_tags": ["contrastive_examples"],
        },
    ))

    assert result["component_strategy_plan"]["recommended"]["learning_sequence"]
    assert result["component_strategy_summary"]["selected_component_types"]
    assert route_after_teacher_approval(TeachingPackState(
        run_id="cs08-stage-flow",
        teacher_approved=True,
        component_strategy_plan=result["component_strategy_plan"],
        artifacts=[],
    )) == "artifact_workflow"
    reset_features()


async def test_flag_off_and_old_planless_runs_still_generate_artifacts(stub_section_prose) -> None:
    assert "provisional_component_strategy" not in {stage.value for stage in teaching_pack_stages(False)}
    fixture = _old_run_state()

    result = await build_hierarchical_artifacts(fixture)

    assert result["artifacts"][0]["artifact_type"] == "lesson"
    assert result["artifacts"][0]["sections"]


def _request(fixture_name: str) -> ComponentStrategyRequest:
    return ComponentStrategyRequest.model_validate_json((FIXTURE_DIR / fixture_name).read_text())


def _old_run_state() -> dict[str, object]:
    import json

    return json.loads((FIXTURE_DIR / "cs08_old_run_planless_state.json").read_text())


def _lesson_plan(subject: str = "language") -> dict[str, object]:
    return {
        "topic": "Vocabulary boundaries",
        "grade_level": "Grade 5",
        "subject": subject,
        "duration_minutes": 45,
        "learning_objectives": [{"objective_id": "LO-1", "objective_revision": "rev-1", "description": "Compare confusable words", "bloom_level": "understand"}],
        "learning_plan": {"present_content": "Model", "elicit_performance": "Practice"},
        "assessment_checkpoints": [{"type": "exit_ticket", "description": "Choose the correct word."}],
    }


def _research_bundle() -> dict[str, object]:
    return {
        "topic": "Vocabulary boundaries",
        "key_findings": ["Contrastive examples help separate confusable meanings"],
        "sources": [{"title": "Source", "verification_status": "VERIFIED"}],
    }


def _strategy_components(artifact: dict[str, object]) -> list[dict[str, object]]:
    components: list[dict[str, object]] = []
    sections = artifact["sections"]
    assert isinstance(sections, list)
    for section in sections:
        assert isinstance(section, dict)
        for component in section.get("components", []):
            if isinstance(component, dict) and "strategy_slot_id" in component:
                components.append(component)
    return components
