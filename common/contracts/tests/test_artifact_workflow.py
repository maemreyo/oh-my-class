from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.artifact_workflow import (
    ArtifactGenerationInput,
    ArtifactWorkflowState,
)
from common.contracts.research_brief import ArtifactResearchGuidance, ResearchBrief
from common.contracts.run_contract import ArtifactType, ContractRevisionMeta, RunContract


def test_workflow_state_tracks_artifact_execution_fields() -> None:
    state = ArtifactWorkflowState(
        workflow_id="workflow-1",
        run_id="run-1",
        artifact_id="lesson-1",
        artifact_type="lesson",
        status="queued",
        attempts=0,
        contract_revision_id=1,
        research_guidance_id="guidance-lesson",
        validation_status="pending",
        judge_status="pending",
        snapshot_refs=[],
        last_error=None,
    )

    assert state.artifact_type == "lesson"
    assert state.status == "queued"
    assert state.contract_revision_id == 1


def test_workflow_state_accepts_drill_as_v1_core_artifact() -> None:
    state = ArtifactWorkflowState(
        workflow_id="workflow-1",
        run_id="run-1",
        artifact_id="drill-1",
        artifact_type="drill",
        status="queued",
        attempts=0,
        contract_revision_id=1,
        research_guidance_id="guidance-drill",
        validation_status="pending",
        judge_status="pending",
        snapshot_refs=[],
        last_error=None,
    )

    assert state.artifact_type == "drill"


def test_workflow_state_refuses_infographic_as_v1_core_artifact() -> None:
    with pytest.raises(ValidationError):
        ArtifactWorkflowState.model_validate({
            "workflow_id": "workflow-1",
            "run_id": "run-1",
            "artifact_id": "infographic-1",
            "artifact_type": "infographic",
            "status": "queued",
            "attempts": 0,
            "contract_revision_id": 1,
            "research_guidance_id": "guidance-infographic",
            "validation_status": "pending",
            "judge_status": "pending",
            "snapshot_refs": [],
        })


def test_generation_input_carries_drill_contract_scope_explicitly() -> None:
    payload = ArtifactGenerationInput(
        artifact_type="drill",
        lesson_blueprint={"objectives": ["Compare fractions"]},
        contract=_contract(artifact_types=["lesson", "drill"]),
        research_brief=ResearchBrief(topic="Fractions", subject="math"),
        research_guidance=ArtifactResearchGuidance(
            artifact_type="drill",
            guidance=["Use short fluency repetitions after the lesson model."],
            citation_ids=[],
        ),
        visual_spec={"theme": "default"},
        dependencies=["lesson"],
    )

    assert payload.artifact_type == "drill"
    assert payload.dependencies == ["lesson"]


def test_generation_input_carries_contract_research_and_dependencies() -> None:
    payload = ArtifactGenerationInput(
        artifact_type="quiz",
        lesson_blueprint={"objectives": ["Compare fractions"]},
        contract=_contract(artifact_types=["lesson", "quiz"]),
        research_brief=ResearchBrief(topic="Fractions", subject="math"),
        research_guidance=ArtifactResearchGuidance(
            artifact_type="quiz",
            guidance=["Include why-wrong explanations."],
            citation_ids=[],
        ),
        visual_spec={"theme": "default"},
        dependencies=["lesson"],
    )

    assert payload.artifact_type == "quiz"
    assert payload.dependencies == ["lesson"]
    assert payload.research_guidance.guidance == ["Include why-wrong explanations."]


def _contract(*, artifact_types: list[ArtifactType]) -> RunContract:
    return RunContract(
        contract_id="contract-1",
        run_id="run-1",
        teacher_id="teacher-1",
        topic="Fractions",
        grade_band="Grade 5",
        subject="math",
        locale="en-US",
        instruction_language="en",
        curriculum="Common Core",
        citation_locale="en-US",
        artifact_types=artifact_types,
        export_formats=["html"],
        research_policy="standard",
        config_version="test",
        config_hash="0" * 64,
        revision_meta=ContractRevisionMeta(
            revision=1,
            actor="system",
            source="request",
            reason="test",
            effective_stage="artifact_generation",
        ),
    )
