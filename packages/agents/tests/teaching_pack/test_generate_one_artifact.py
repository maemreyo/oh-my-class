from __future__ import annotations

import pytest

from packages.agents.sub_agents.content_creator.hierarchical import build_hierarchical_artifacts
from packages.agents.teaching_pack.content_orchestrator import InMemoryArtifactContentStore
from packages.agents.teaching_pack.generate_one_artifact import generate_one_artifact
from packages.agents.teaching_pack.stages import StageEnum
from packages.quality.layer2_content.pedagogical import check_pedagogical_metrics


def _payload(artifact_type: str = "lesson") -> dict[str, object]:
    return {
        "run_id": "run-1",
        "artifact_generation_id": "gen-1",
        "artifact_type": artifact_type,
        "lesson_plan": {"topic": "Fractions"},
        "research_brief": {"sources": []},
        "theme": "default",
        "revision_feedback": "",
        "dependency_artifact_references": [],
    }


def _lesson_plan_with_bloom() -> dict[str, object]:
    return {
        "topic": "Fractions",
        "grade_level": "Grade 6",
        "learning_objectives": [
            {"description": "Students understand fractions", "bloom_level": "understand"},
            {"description": "Students apply fractions", "bloom_level": "apply"},
        ],
        "learning_plan": {
            "present_content": "Model equivalent fractions.",
            "elicit_performance": "Practice with feedback.",
        },
    }


def _artifact(artifact_type: str = "lesson") -> dict[str, object]:
    return {
        "artifact_id": f"{artifact_type}-1",
        "artifact_type": artifact_type,
        "theme": "default",
        "title": f"{artifact_type.title()} Artifact",
        "sections": [{"title": "Intro", "content": "Use unit fractions."}],
        "metadata": {},
        "accessibility": {"language": "en"},
    }


@pytest.mark.anyio
async def test_generation_without_store_returns_status_without_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_state: dict[str, object] = {}

    async def fake_content_creator_node(state: dict[str, object]) -> dict[str, object]:
        captured_state.update(state)
        assert state["artifact_types"] == ["lesson"]
        return {"artifacts": [_artifact("lesson")]}

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fake_content_creator_node,
    )

    result = await generate_one_artifact(_payload("lesson"))

    assert captured_state["use_hierarchical_creator"] is True
    assert set(result) == {"artifact_workflow_states"}
    assert result["artifact_workflow_states"] == [{
        "workflow_id": "gen-1:lesson",
        "artifact_generation_id": "gen-1",
        "artifact_id": "lesson-1",
        "artifact_type": "lesson",
        "status": "passed",
    }]


@pytest.mark.anyio
async def test_store_backed_generation_returns_reference_without_chunk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_content_creator_node(_state: dict[str, object]) -> dict[str, object]:
        return {"artifacts": [_artifact("lesson")]}

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fake_content_creator_node,
    )

    result = await generate_one_artifact(_payload("lesson"), InMemoryArtifactContentStore())

    assert "artifact_references" in result
    assert result["artifact_references"] == [{
        "document_id": "gen-1:lesson-1",
        "artifact_id": "lesson-1",
        "artifact_type": "lesson",
        "generation_id": "gen-1",
        "version": 1,
        "title": "Lesson Artifact",
    }]


async def test_hierarchical_artifact_carries_bloom_evidence_for_pedagogical_gate(stub_section_prose) -> None:
    _ = stub_section_prose
    result = await build_hierarchical_artifacts({
        "lesson_plan": _lesson_plan_with_bloom(),
        "research_bundle": {"key_findings": ["Fractions represent equal parts of a whole."], "sources": []},
        "artifact_types": ["lesson"],
        "theme": "default",
        "run_id": "run-1",
        "current_step": StageEnum.ARTIFACT_WORKFLOW,
        "artifacts": [],
    })

    artifact = result["artifacts"][0]
    pedagogical = check_pedagogical_metrics(artifact, lesson_plan=_lesson_plan_with_bloom())

    assert artifact["metadata"]["covered_bloom_levels"] == ["understand", "apply"]
    assert pedagogical.metrics["bloom_coverage"] == "passed"


@pytest.mark.anyio
async def test_schema_mismatch_returns_failed_workflow_state(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_content_creator_node(_state: dict[str, object]) -> dict[str, object]:
        return {"artifacts": [{"artifact_type": "lesson", "title": "No sections"}]}

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fake_content_creator_node,
    )

    result = await generate_one_artifact(_payload("lesson"))

    assert "artifact_references" not in result
    assert result["artifact_workflow_states"][0]["status"] == "failed"
    assert result["artifact_workflow_states"][0]["error_class"] == "ValidationError"
    assert len(str(result["artifact_workflow_states"][0]["error_summary"])) <= 240


@pytest.mark.anyio
async def test_artifact_type_mismatch_returns_failed_workflow_state(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_content_creator_node(_state: dict[str, object]) -> dict[str, object]:
        return {"artifacts": [_artifact("quiz")]}

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fake_content_creator_node,
    )

    result = await generate_one_artifact(_payload("lesson"))

    assert "artifact_references" not in result
    assert result["artifact_workflow_states"][0]["status"] == "failed"
    assert result["artifact_workflow_states"][0]["error_class"] == "ArtifactTypeMismatchError"


@pytest.mark.anyio
async def test_infrastructure_error_is_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_content_creator_node(_state: dict[str, object]) -> dict[str, object]:
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fake_content_creator_node,
    )

    with pytest.raises(RuntimeError, match="provider unavailable"):
        await generate_one_artifact(_payload("lesson"))
