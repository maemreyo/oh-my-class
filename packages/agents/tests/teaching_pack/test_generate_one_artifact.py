from __future__ import annotations

import pytest

from common.contracts.answer_set import AnswerEntry, AnswerSet
from common.contracts.artifact import ArtifactContent
from packages.agents.sub_agents.content_creator.hierarchical import build_hierarchical_artifacts
from packages.agents.config.features import reset_features
from packages.agents.teaching_pack.content_orchestrator import ArtifactPersistenceResult, InMemoryArtifactContentStore
from packages.agents.teaching_pack.generate_one_artifact import (
    UnsupportedArtifactCapabilityError,
    generate_one_artifact,
)
from packages.agents.teaching_pack.stages import StageEnum
from packages.quality.layer2_content.pedagogical import check_pedagogical_metrics


@pytest.fixture(autouse=True)
def _reset_feature_cache() -> None:
    """Guards every test in this file against feature-flag cache leakage
    from `_enable_generic_fallback` below (the module-level `_FEATURES`
    singleton otherwise survives past `monkeypatch.setenv`'s teardown)."""
    reset_features()
    yield
    reset_features()


def _enable_generic_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """#464: the generic content_creator_node path is experimental/dev-only
    behind this flag now -- these tests deliberately force `get_specialist`
    to return None to exercise that glue code in isolation, so they must
    opt in explicitly rather than relying on it being reachable by default."""
    monkeypatch.setenv("FEATURE_GENERIC_CONTENT_CREATOR_FALLBACK_V1", "true")
    reset_features()


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
    monkeypatch.setattr("packages.agents.teaching_pack.generate_one_artifact.get_specialist", lambda _type: None)
    _enable_generic_fallback(monkeypatch)

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
    monkeypatch.setattr("packages.agents.teaching_pack.generate_one_artifact.get_specialist", lambda _type: None)
    _enable_generic_fallback(monkeypatch)

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


@pytest.mark.anyio
async def test_assessment_generation_persists_student_projection_without_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_content_creator_node(_state: dict[str, object]) -> dict[str, object]:
        return {"artifacts": [{
            **_artifact("quiz"),
            "sections": [{"components": [{
                "type": "question_card",
                "id": "question-1",
                "text": "Which fraction is one half?",
                "options": {"A": "2/4", "B": "1/3"},
                "answer": "A",
                "explain": "Two fourths equals one half.",
            }]}],
        }]}

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fake_content_creator_node,
    )
    monkeypatch.setattr("packages.agents.teaching_pack.generate_one_artifact.get_specialist", lambda _type: None)
    _enable_generic_fallback(monkeypatch)
    store = InMemoryArtifactContentStore()

    result = await generate_one_artifact(_payload("quiz"), store)
    persisted = await store.read_projection(result["artifact_references"][0]["document_id"])

    assert "answer_set" not in persisted.metadata
    assert "answer" not in persisted.sections[0]["components"][0]


@pytest.mark.anyio
async def test_answer_key_generation_reads_teacher_only_answer_set_from_dependency_store() -> None:
    store = InMemoryArtifactContentStore()
    quiz = ArtifactContent.model_validate({
        **_artifact("quiz"),
        "sections": [{"components": [{
            "type": "question_card",
            "id": "question-1",
            "text": "Which fraction is one half?",
            "options": {"A": "2/4", "B": "1/3"},
            "answer": "A",
            "explain": "Two fourths equals one half.",
        }]}],
    })
    answer_set = AnswerSet(
        answer_set_id="answers-pending",
        source_document_id="pending",
        source_version=1,
        entries=[AnswerEntry(entity_id="answer-question-1", question_id="question-1", correct_option_ids=["A"])],
    )
    reference = await store.persist_result(
        "run-1", "gen-quiz", ArtifactPersistenceResult(artifact=quiz, answer_set=answer_set), "quiz-1",
    )
    payload = _payload("answer_key")
    payload["dependency_artifact_references"] = [reference.as_state()]

    result = await generate_one_artifact(payload, store)
    answer_key = await store.read_projection(result["artifact_references"][0]["document_id"])

    assert answer_key.artifact_type == "answer_key"
    assert answer_key.sections[0]["components"][0]["text"] == "Answer: A"


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
    monkeypatch.setattr("packages.agents.teaching_pack.generate_one_artifact.get_specialist", lambda _type: None)
    _enable_generic_fallback(monkeypatch)

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
    monkeypatch.setattr("packages.agents.teaching_pack.generate_one_artifact.get_specialist", lambda _type: None)
    _enable_generic_fallback(monkeypatch)

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
    monkeypatch.setattr("packages.agents.teaching_pack.generate_one_artifact.get_specialist", lambda _type: None)
    _enable_generic_fallback(monkeypatch)

    with pytest.raises(RuntimeError, match="provider unavailable"):
        await generate_one_artifact(_payload("lesson"))


@pytest.mark.anyio
async def test_undeclared_type_never_reaches_content_creator_node_with_flag_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#464 required guard test: "no production code path calls
    content_creator_node as an undeclared fallback." The flag defaults off
    (no `_enable_generic_fallback` call here), so an undeclared artifact
    type must raise UnsupportedArtifactCapabilityError before ever reaching
    content_creator_node -- proven by making that function explode if
    called at all."""
    async def exploding_content_creator_node(_state: dict[str, object]) -> dict[str, object]:
        raise AssertionError("content_creator_node must not be called when the fallback is off")

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        exploding_content_creator_node,
    )
    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.get_specialist", lambda _type: None,
    )

    result = await generate_one_artifact(_payload("an_undeclared_type"))

    assert "artifact_references" not in result
    state = result["artifact_workflow_states"][0]
    assert state["status"] == "failed"
    assert state["error_class"] == UnsupportedArtifactCapabilityError.__name__


@pytest.mark.anyio
async def test_lineage_stamp_is_present_on_the_persisted_projection() -> None:
    store = InMemoryArtifactContentStore()
    payload = _payload("lesson")
    payload["lesson_plan"] = _lesson_plan_with_bloom()

    result = await generate_one_artifact(payload, store)
    persisted = await store.read_projection(result["artifact_references"][0]["document_id"])

    lineage = persisted.metadata["specialist_lineage"]
    assert lineage == {
        "artifact_type": "lesson",
        "specialist_id": "registry:lesson",
        "module_version": "v1",
        "consumed_content_brief_fields": [],
    }


def test_orchestrator_request_is_the_adr_053_name_for_the_payload_shape() -> None:
    """#464: OrchestratorRequest is an alias, not a parallel type."""
    from packages.agents.teaching_pack.generate_one_artifact import (
        GenerateOneArtifactPayload,
        OrchestratorRequest,
    )

    assert OrchestratorRequest is GenerateOneArtifactPayload
