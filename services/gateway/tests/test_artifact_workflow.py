from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from common.contracts.artifact import ArtifactContent
from common.contracts.artifact_workflow import ArtifactGenerationInput
from common.contracts.research_brief import ArtifactResearchGuidance, ResearchBrief
from common.contracts.run_contract import ArtifactType, ContractRevisionMeta, RunContract
from services.gateway.artifact_workflow import (
    ArtifactGenerator,
    ArtifactOrchestrator,
    ArtifactOrchestratorConfig,
    GenerationError,
)


@dataclass(slots=True)
class RecordingGenerator(ArtifactGenerator):
    active: int = 0
    max_active: int = 0
    calls: list[str] = field(default_factory=list)
    attempts: dict[str, int] = field(default_factory=dict)
    fail_once: frozenset[str] = frozenset()
    fail_always: frozenset[str] = frozenset()
    guidance_by_artifact: dict[str, ArtifactResearchGuidance] = field(default_factory=dict)

    async def generate(self, payload: ArtifactGenerationInput) -> ArtifactContent:
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        self.calls.append(payload.artifact_type)
        self.guidance_by_artifact[payload.artifact_type] = payload.research_guidance
        self.attempts[payload.artifact_type] = self.attempts.get(payload.artifact_type, 0) + 1
        try:
            if payload.artifact_type in self.fail_always:
                raise GenerationError("provider_error", "provider failed")
            if (
                payload.artifact_type in self.fail_once
                and self.attempts[payload.artifact_type] == 1
            ):
                raise GenerationError("malformed_json", "malformed JSON")
            return ArtifactContent(
                artifact_type=payload.artifact_type,
                title=f"{payload.artifact_type.title()} Artifact",
                sections=[{"title": "Section", "body": "oh-my-class content"}],
                accessibility={"language": "en", "alt_texts": {}},
            )
        finally:
            self.active -= 1


class TestArtifactOrchestrator:
    @pytest.mark.anyio
    async def test_generates_core_artifacts_with_dependencies_and_limit(self) -> None:
        generator = RecordingGenerator()
        orchestrator = ArtifactOrchestrator(
            generator,
            ArtifactOrchestratorConfig(max_parallel_artifacts=2, max_attempts=2),
        )

        result = await orchestrator.generate_core_artifacts(
            _request(["lesson", "worksheet", "quiz", "recap"]),
        )

        assert [artifact.artifact_type for artifact in result.passed_artifacts] == [
            "lesson", "worksheet", "quiz", "recap",
        ]
        assert generator.calls[0] == "lesson"
        assert generator.calls.index("recap") > generator.calls.index("lesson")
        assert generator.max_active <= 2
        assert all(state.status == "passed" for state in result.states)

    @pytest.mark.anyio
    async def test_retries_only_failed_artifact_and_keeps_passed_artifacts(self) -> None:
        generator = RecordingGenerator(fail_once=frozenset({"quiz"}))
        orchestrator = ArtifactOrchestrator(
            generator,
            ArtifactOrchestratorConfig(max_parallel_artifacts=1, max_attempts=2),
        )

        result = await orchestrator.generate_core_artifacts(_request(["lesson", "quiz", "recap"]))

        assert [artifact.artifact_type for artifact in result.passed_artifacts] == [
            "lesson", "quiz", "recap",
        ]
        assert generator.attempts == {"lesson": 1, "quiz": 2, "recap": 1}
        quiz_state = next(state for state in result.states if state.artifact_type == "quiz")
        assert quiz_state.attempts == 2
        assert quiz_state.status == "passed"
        assert quiz_state.last_error is None

    @pytest.mark.anyio
    async def test_one_artifact_failure_does_not_discard_passed_artifacts(self) -> None:
        generator = RecordingGenerator(fail_always=frozenset({"quiz"}))
        orchestrator = ArtifactOrchestrator(
            generator,
            ArtifactOrchestratorConfig(max_parallel_artifacts=1, max_attempts=2),
        )

        result = await orchestrator.generate_core_artifacts(_request(["lesson", "quiz", "recap"]))

        assert [artifact.artifact_type for artifact in result.passed_artifacts] == ["lesson"]
        quiz_state = next(state for state in result.states if state.artifact_type == "quiz")
        recap_state = next(state for state in result.states if state.artifact_type == "recap")
        assert quiz_state.status == "failed"
        assert quiz_state.last_error == "provider_error: provider failed"
        assert recap_state.status == "skipped"

    @pytest.mark.anyio
    async def test_generation_error_is_redacted_and_truncated(self) -> None:
        secret = "sk-live-" + "x" * 80
        generator = RecordingGenerator(fail_always=frozenset({"quiz"}))
        orchestrator = ArtifactOrchestrator(
            generator,
            ArtifactOrchestratorConfig(max_parallel_artifacts=1, max_attempts=1),
        )

        async def fail_with_secret(payload: ArtifactGenerationInput) -> ArtifactContent:
            if payload.artifact_type == "quiz":
                raise GenerationError("provider_error", f"token={secret} provider failed")
            return await RecordingGenerator().generate(payload)

        generator.generate = fail_with_secret

        result = await orchestrator.generate_core_artifacts(_request(["lesson", "quiz"]))

        quiz_state = next(state for state in result.states if state.artifact_type == "quiz")
        assert quiz_state.last_error is not None
        assert secret not in quiz_state.last_error
        assert "[redacted]" in quiz_state.last_error
        assert len(quiz_state.last_error) <= 500

    @pytest.mark.anyio
    async def test_quality_gate_blocks_invalid_generated_artifact(self) -> None:
        generator = RecordingGenerator()
        orchestrator = ArtifactOrchestrator(
            generator,
            ArtifactOrchestratorConfig(max_parallel_artifacts=1, max_attempts=1),
        )

        async def fail_quality(payload: ArtifactGenerationInput) -> ArtifactContent:
            return ArtifactContent(
                artifact_type=payload.artifact_type,
                title="Invalid Artifact",
                sections=[{"content": "TODO answer: 42"}],
            )

        generator.generate = fail_quality

        result = await orchestrator.generate_core_artifacts(_request(["lesson"]))

        lesson_state = result.states[0]
        assert result.passed_artifacts == []
        assert lesson_state.status == "failed"
        assert lesson_state.last_error == "quality_gate_failed: placeholder_content"

    @pytest.mark.anyio
    async def test_quality_gate_repairs_answer_key_before_regenerating(self) -> None:
        generator = RecordingGenerator()
        orchestrator = ArtifactOrchestrator(
            generator,
            ArtifactOrchestratorConfig(max_parallel_artifacts=1, max_attempts=2),
        )

        async def leak_answer_key(payload: ArtifactGenerationInput) -> ArtifactContent:
            return ArtifactContent(
                artifact_type=payload.artifact_type,
                title="Lesson Artifact",
                sections=[{"content": "Question", "answer": "correct: 42"}],
                accessibility={"language": "en"},
            )

        generator.generate = leak_answer_key

        result = await orchestrator.generate_core_artifacts(_request(["lesson"]))

        assert generator.calls == []
        assert result.states[0].status == "passed"
        assert result.passed_artifacts[0].sections[0]["teacher_only"] is True

    def test_refuses_unsupported_v2_core_artifact_type(self) -> None:
        orchestrator = ArtifactOrchestrator(RecordingGenerator())

        with pytest.raises(ValueError, match="unsupported V2 artifact type"):
            orchestrator.plan(_request(["lesson", "drill"]))

    def test_refuses_artifact_plan_with_missing_dependency(self) -> None:
        orchestrator = ArtifactOrchestrator(RecordingGenerator())

        with pytest.raises(ValueError, match="missing V2 artifact dependency"):
            orchestrator.plan(_request(["worksheet"]))

    def test_queued_artifact_id_fits_contract_with_long_run_id(self) -> None:
        orchestrator = ArtifactOrchestrator(RecordingGenerator())

        plan = orchestrator.plan(_request(["lesson"], run_id="r" * 64))

        assert len(plan) == 1

    @pytest.mark.anyio
    async def test_passes_per_artifact_research_guidance_to_generator(self) -> None:
        generator = RecordingGenerator()
        orchestrator = ArtifactOrchestrator(generator)

        await orchestrator.generate_core_artifacts(_request(["lesson", "quiz"]))

        assert generator.guidance_by_artifact["lesson"].guidance == ["Use manipulatives"]
        assert generator.guidance_by_artifact["lesson"].citation_ids == ["source-lesson"]
        assert generator.guidance_by_artifact["quiz"].guidance == ["Use mixed difficulty"]
        assert generator.guidance_by_artifact["quiz"].citation_ids == ["source-quiz"]


def _request(
    artifact_types: list[ArtifactType],
    *,
    run_id: str = "run-1",
) -> ArtifactGenerationInput:
    contract = RunContract(
        contract_id="contract-1",
        run_id=run_id,
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
    return ArtifactGenerationInput(
        artifact_type="lesson",
        lesson_blueprint={"objectives": ["Compare fractions"]},
        contract=contract,
        research_brief=ResearchBrief(
            topic="Fractions",
            subject="math",
            artifact_guidance=[
                ArtifactResearchGuidance(
                    artifact_type="lesson",
                    guidance=["Use manipulatives"],
                    citation_ids=["source-lesson"],
                ),
                ArtifactResearchGuidance(
                    artifact_type="quiz",
                    guidance=["Use mixed difficulty"],
                    citation_ids=["source-quiz"],
                ),
            ],
        ),
        research_guidance=ArtifactResearchGuidance(artifact_type="lesson"),
        visual_spec={"theme": "default"},
        dependencies=[],
    )
