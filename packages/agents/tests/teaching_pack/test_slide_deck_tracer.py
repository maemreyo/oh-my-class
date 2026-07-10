from __future__ import annotations

import json

import pytest

from packages.agents.sub_agents.content_creator.hierarchical import build_hierarchical_artifacts
from packages.agents.teaching_pack.artifact_fanout import route_after_artifact_workflow
from packages.agents.teaching_pack.content_orchestrator import InMemoryArtifactContentStore
from packages.agents.teaching_pack.generate_one_artifact import generate_one_artifact
from packages.agents.teaching_pack.stages import StageEnum


def _lesson_plan() -> dict[str, object]:
    return {
        "topic": "Equivalent fractions",
        "grade_level": "Grade 5",
        "learning_objectives": [
            {"description": "Explain why two fractions are equivalent."},
        ],
        "learning_plan": {"present_content": {}, "assess_performance": {}},
    }


def _research_brief() -> dict[str, object]:
    return {
        "sources": [
            {
                "id": "src-fractions-standard",
                "title": "Grade 5 Fractions Standard",
                "citation": "CCSS 5.NF.A",
            },
        ],
    }


@pytest.mark.anyio
async def test_hierarchical_content_creator_returns_slide_deck_artifact(stub_section_prose) -> None:
    # SDE-01: slide_deck now makes a real llm_client call (ContentMaterializer
    # wording) too, so this needs the same stub as the other artifact types to
    # stay fast/hermetic instead of hitting a live 9router.
    _ = stub_section_prose
    result = await build_hierarchical_artifacts({
        "lesson_plan": _lesson_plan(),
        "research_bundle": _research_brief(),
        "artifact_types": ["slide_deck"],
        "theme": "default",
        "run_id": "run-slide-tracer",
        "current_step": StageEnum.ARTIFACT_WORKFLOW,
        "artifacts": [],
    })

    artifact = result["artifacts"][0]

    assert artifact["artifact_type"] == "slide_deck"
    assert artifact["metadata"]["slide_deck_data"]["deck_id"] == "slide-deck-run-slide-tracer"
    assert artifact["sections"][0]["slide_deck"]["slides"][4]["interactions"][0]["teacher_only"]["separation"] == "teacher_only_projection"


@pytest.mark.anyio
async def test_generate_one_artifact_persists_slide_deck_without_llm(stub_section_prose) -> None:
    _ = stub_section_prose
    content_store = InMemoryArtifactContentStore()
    result = await generate_one_artifact({
        "run_id": "run-slide-one",
        "artifact_generation_id": "run-slide-one:artifact:1",
        "artifact_type": "slide_deck",
        "lesson_plan": _lesson_plan(),
        "research_brief": _research_brief(),
        "theme": "default",
        "revision_feedback": "",
        "dependency_artifact_references": [],
    }, content_store)

    reference = result["artifact_references"][0]
    artifact = await content_store.read_projection(reference["document_id"])
    workflow = result["artifact_workflow_states"][0]

    assert artifact.artifact_type == "slide_deck"
    assert artifact.metadata["slide_deck_data"]["deck_id"] == "slide-deck-run-slide-one"
    assert workflow["artifact_type"] == "slide_deck"
    assert workflow["status"] == "passed"


@pytest.mark.anyio
async def test_generate_one_artifact_reaches_content_materialization_llm_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """ADR-032 live-path proof for SDE-01: the LLM call inside ContentMaterializer
    is reachable from the real production entrypoint (`generate_one_artifact`, the
    actual teaching-pack graph node), not just from a fixture that hand-constructs
    the phase's `AssembledSlideDeckInput`/`PedagogicalPlan` and calls
    `materialize_deck` directly. Overrides the shared llm stub with real,
    distinguishing content and confirms it surfaces in the artifact produced by
    the full generate_one_artifact -> content_creator_node ->
    build_hierarchical_artifacts -> build_slide_deck_artifact ->
    SlideDeckEngine.generate -> materialize_deck chain.
    """
    from packages.agents import llm

    marker_wording = {
        "vocabulary_body": "LIVE_PATH_PROOF_MARKER vocabulary body",
        "vocabulary_practice_body": "LIVE_PATH_PROOF_MARKER vocabulary practice",
        "example_body": "LIVE_PATH_PROOF_MARKER example body",
        "sentence_stem": "LIVE_PATH_PROOF_MARKER sentence stem",
        "check_prompt": "LIVE_PATH_PROOF_MARKER check prompt",
        "practice_correct_option": "LIVE_PATH_PROOF_MARKER correct option",
        "practice_distractor_a": "LIVE_PATH_PROOF_MARKER distractor a",
        "practice_distractor_b": "LIVE_PATH_PROOF_MARKER distractor b",
        "teacher_rationale": "LIVE_PATH_PROOF_MARKER rationale",
        "exit_prompt": "LIVE_PATH_PROOF_MARKER exit prompt",
    }

    async def fake_complete_json_chat(
        *,
        model: str,
        messages: list[object],
        temperature: float,
        tags: list[str],
    ) -> str:
        _ = (model, messages, temperature, tags)
        return json.dumps(marker_wording)

    monkeypatch.setattr(llm, "complete_json_chat", fake_complete_json_chat)

    content_store = InMemoryArtifactContentStore()
    result = await generate_one_artifact({
        "run_id": "run-slide-live-path",
        "artifact_generation_id": "run-slide-live-path:artifact:1",
        "artifact_type": "slide_deck",
        "lesson_plan": _lesson_plan(),
        "research_brief": _research_brief(),
        "theme": "default",
        "revision_feedback": "",
        "dependency_artifact_references": [],
    }, content_store)

    reference = result["artifact_references"][0]
    artifact = await content_store.read_projection(reference["document_id"])
    slide_deck_json = json.dumps(artifact.metadata["slide_deck_data"])

    assert "LIVE_PATH_PROOF_MARKER" in slide_deck_json
    assert artifact.metadata["slide_deck_trace"]["llm_calls"] == 1


def test_slide_deck_fanout_runs_after_lesson_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", raising=False)
    state = {
        "run_id": "run-slide-fanout",
        "artifact_generation_id": "run-slide-fanout:artifact:1",
        "artifact_generation_revision": 1,
        "artifact_wave_index": 0,
        "artifact_types": ["lesson", "slide_deck"],
        "lesson_plan": _lesson_plan(),
        "research_brief": _research_brief(),
        "contract": {"theme": "default", "artifact_types": ["lesson", "slide_deck"]},
        "artifact_workflow_states": [
            {
                "artifact_generation_id": "run-slide-fanout:artifact:1",
                "artifact_type": "lesson",
                "status": "passed",
            },
        ],
        "artifact_references": [{
            "document_id": "run-slide-fanout:artifact:1:lesson-1",
            "artifact_id": "lesson-1",
            "artifact_type": "lesson",
            "generation_id": "run-slide-fanout:artifact:1",
            "version": 1,
            "title": "Lesson",
        }],
    }

    routed = route_after_artifact_workflow({**state, "artifact_wave_index": 1})

    assert not isinstance(routed, str)
    assert len(routed) == 1
    assert routed[0].node == "generate_one_artifact"
    assert routed[0].arg["artifact_type"] == "slide_deck"
    assert routed[0].arg["dependency_artifact_references"][0]["artifact_id"] == "lesson-1"
