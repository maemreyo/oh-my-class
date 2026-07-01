from __future__ import annotations

import pytest

from packages.agents.teaching_pack.generate_one_artifact import generate_one_artifact


def _payload(artifact_type: str = "lesson") -> dict[str, object]:
    return {
        "run_id": "run-1",
        "artifact_generation_id": "gen-1",
        "artifact_type": artifact_type,
        "lesson_plan": {"topic": "Fractions"},
        "research_brief": {"sources": []},
        "theme": "default",
        "revision_feedback": "",
        "dependency_artifacts": [],
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
async def test_success_returns_chunk_and_passed_workflow_state(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_content_creator_node(state: dict[str, object]) -> dict[str, object]:
        assert state["artifact_types"] == ["lesson"]
        return {"artifacts": [_artifact("lesson")]}

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fake_content_creator_node,
    )

    result = await generate_one_artifact(_payload("lesson"))

    assert set(result) == {"artifact_chunks", "artifact_workflow_states"}
    assert result["artifact_chunks"] == [{**_artifact("lesson"), "artifact_generation_id": "gen-1"}]
    assert result["artifact_workflow_states"] == [{
        "workflow_id": "gen-1:lesson",
        "artifact_generation_id": "gen-1",
        "artifact_id": "lesson-1",
        "artifact_type": "lesson",
        "status": "passed",
    }]


@pytest.mark.anyio
async def test_schema_mismatch_returns_failed_workflow_state(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_content_creator_node(_state: dict[str, object]) -> dict[str, object]:
        return {"artifacts": [{"artifact_type": "lesson", "title": "No sections"}]}

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fake_content_creator_node,
    )

    result = await generate_one_artifact(_payload("lesson"))

    assert "artifact_chunks" not in result
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

    assert "artifact_chunks" not in result
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
