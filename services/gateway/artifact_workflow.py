"""Legacy gateway artifact workflow primitives.

The production teaching-pack graph now uses ADR-020 LangGraph ``Send`` fan-out
through ``packages.agents.teaching_pack``. This module remains for gateway-level
fallback/test coverage and historical Pipeline V2 helpers; it is not the
production teaching-pack artifact orchestrator.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, assert_never
from uuid import NAMESPACE_URL, uuid5

import anyio

from common.contracts.artifact_workflow import (
    ArtifactGenerationInput,
    ArtifactWorkflowState,
    CoreArtifactType,
)
from common.contracts.research_brief import ArtifactResearchGuidance
from services.gateway.artifact_workflow_errors import (
    GenerationError,
    UnsupportedArtifactTypeError,
    generation_error_summary,
    quality_error_summary,
    terminal_generation_failure,
)
from services.gateway.healing_executors import try_heal_artifact
from services.gateway.quality_gates import validate_artifact_content

if TYPE_CHECKING:
    from common.contracts.artifact import ArtifactContent
    from common.contracts.run_contract import ArtifactType

_CORE_ARTIFACTS: tuple[CoreArtifactType, ...] = ("lesson", "worksheet", "quiz", "drill", "recap")
_DEPENDENCIES: dict[CoreArtifactType, tuple[CoreArtifactType, ...]] = {
    "lesson": (),
    "worksheet": ("lesson",),
    "quiz": ("lesson",),
    "drill": ("lesson",),
    "recap": ("lesson", "quiz"),
}


class ArtifactGenerator(Protocol):
    async def generate(self, payload: ArtifactGenerationInput) -> ArtifactContent:
        ...


@dataclass(frozen=True, slots=True)
class MissingArtifactDependencyError(ValueError):
    artifact_type: CoreArtifactType
    dependency: CoreArtifactType

    def __str__(self) -> str:
        return (
            f"missing V2 artifact dependency: {self.artifact_type} requires "
            f"{self.dependency}"
        )


@dataclass(frozen=True, slots=True)
class ArtifactOrchestratorConfig:
    max_parallel_artifacts: int = 1
    max_attempts: int = 2


@dataclass(frozen=True, slots=True)
class ArtifactWorkflowResult:
    states: list[ArtifactWorkflowState]
    passed_artifacts: list[ArtifactContent]


@dataclass(frozen=True, slots=True)
class ArtifactPlanItem:
    artifact_type: CoreArtifactType
    dependencies: tuple[CoreArtifactType, ...]


@dataclass(slots=True)
class ArtifactOrchestrator:
    """Gateway fallback orchestrator, not the teaching-pack graph runtime."""

    _generator: ArtifactGenerator
    _config: ArtifactOrchestratorConfig = ArtifactOrchestratorConfig()

    def plan(self, request: ArtifactGenerationInput) -> list[ArtifactPlanItem]:
        artifact_types = _core_artifact_types(request.contract.artifact_types)
        requested = set(artifact_types)
        for artifact_type in artifact_types:
            for dependency in _DEPENDENCIES[artifact_type]:
                if dependency not in requested:
                    raise MissingArtifactDependencyError(artifact_type, dependency)
        return [
            ArtifactPlanItem(artifact_type=artifact_type, dependencies=_DEPENDENCIES[artifact_type])
            for artifact_type in _CORE_ARTIFACTS
            if artifact_type in artifact_types
        ]

    async def generate_core_artifacts(
        self,
        request: ArtifactGenerationInput,
    ) -> ArtifactWorkflowResult:
        plan = self.plan(request)
        limiter = anyio.CapacityLimiter(self._config.max_parallel_artifacts)
        states: dict[CoreArtifactType, ArtifactWorkflowState] = {
            item.artifact_type: _queued_state(request, item.artifact_type) for item in plan
        }
        passed: dict[CoreArtifactType, ArtifactContent] = {}

        for wave in _execution_waves(plan):
            runnable = [item for item in wave if _dependencies_passed(item, passed)]
            skipped = [item for item in wave if item not in runnable]
            for item in skipped:
                states[item.artifact_type] = _skip_state(states[item.artifact_type])
            async with anyio.create_task_group() as task_group:
                for item in runnable:
                    async def run_artifact(artifact_type: CoreArtifactType) -> None:
                        await self._run_one(request, artifact_type, states, passed, limiter)

                    task_group.start_soon(run_artifact, item.artifact_type)

        ordered_states = [states[item.artifact_type] for item in plan]
        ordered_artifacts = [
            passed[item.artifact_type] for item in plan if item.artifact_type in passed
        ]
        return ArtifactWorkflowResult(states=ordered_states, passed_artifacts=ordered_artifacts)

    async def _run_one(
        self,
        request: ArtifactGenerationInput,
        artifact_type: CoreArtifactType,
        states: dict[CoreArtifactType, ArtifactWorkflowState],
        passed: dict[CoreArtifactType, ArtifactContent],
        limiter: anyio.CapacityLimiter,
    ) -> None:
        async with limiter:
            state = _running_state(states[artifact_type])
            states[artifact_type] = state
            for attempt in range(1, self._config.max_attempts + 1):
                state = state.model_copy(update={"attempts": attempt})
                try:
                    artifact = await self._generator.generate(_payload_for(request, artifact_type))
                    report = validate_artifact_content(state.artifact_id, artifact)
                    if not report.passed:
                        healed = try_heal_artifact(state.artifact_id, artifact)
                        if healed is not None:
                            states[artifact_type] = _passed_state(state)
                            passed[artifact_type] = healed
                            return
                        state = _failed_state(
                            state,
                            quality_error_summary(report.issues[0].failure_class),
                        )
                        continue
                    states[artifact_type] = _passed_state(state)
                    passed[artifact_type] = artifact
                    return
                except GenerationError as exc:
                    state = _failed_state(state, generation_error_summary(exc))
            states[artifact_type] = terminal_generation_failure(state)


def _execution_waves(plan: list[ArtifactPlanItem]) -> list[list[ArtifactPlanItem]]:
    done: set[CoreArtifactType] = set()
    remaining = list(plan)
    waves: list[list[ArtifactPlanItem]] = []
    while remaining:
        wave = [item for item in remaining if set(item.dependencies).issubset(done)]
        waves.append(wave)
        for item in wave:
            done.add(item.artifact_type)
            remaining.remove(item)
    return waves


def _core_artifact_types(artifact_types: list[ArtifactType]) -> tuple[CoreArtifactType, ...]:
    core_artifacts: list[CoreArtifactType] = []
    for artifact_type in artifact_types:
        match artifact_type:
            case "lesson" | "worksheet" | "quiz" | "drill" | "recap":
                core_artifacts.append(artifact_type)
            case "infographic":
                raise UnsupportedArtifactTypeError(artifact_type)
            case unreachable:
                assert_never(unreachable)
    return tuple(core_artifacts)


def _dependencies_passed(
    item: ArtifactPlanItem,
    passed: dict[CoreArtifactType, ArtifactContent],
) -> bool:
    return all(dependency in passed for dependency in item.dependencies)


def _payload_for(
    request: ArtifactGenerationInput,
    artifact_type: CoreArtifactType,
) -> ArtifactGenerationInput:
    return request.model_copy(update={
        "artifact_type": artifact_type,
        "research_guidance": _guidance_for(request, artifact_type),
        "dependencies": list(_DEPENDENCIES[artifact_type]),
    })


def _guidance_for(
    request: ArtifactGenerationInput,
    artifact_type: CoreArtifactType,
) -> ArtifactResearchGuidance:
    for guidance in request.research_brief.artifact_guidance:
        if guidance.artifact_type == artifact_type:
            return guidance
    return ArtifactResearchGuidance(artifact_type=artifact_type)


def _queued_state(
    request: ArtifactGenerationInput,
    artifact_type: CoreArtifactType,
) -> ArtifactWorkflowState:
    artifact_id = f"artifact-{uuid5(NAMESPACE_URL, f'{request.contract.run_id}:{artifact_type}')}"
    return ArtifactWorkflowState(
        workflow_id=(
            f"workflow-{uuid5(NAMESPACE_URL, f'{request.contract.run_id}:{artifact_type}')}"
        ),
        run_id=request.contract.run_id,
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        status="queued",
        attempts=0,
        contract_revision_id=request.contract.revision_meta.revision,
        research_guidance_id=f"guidance-{artifact_type}",
        validation_status="pending",
        judge_status="pending",
        snapshot_refs=[],
    )


def _running_state(state: ArtifactWorkflowState) -> ArtifactWorkflowState:
    return state.model_copy(update={"status": "running"})


def _passed_state(state: ArtifactWorkflowState) -> ArtifactWorkflowState:
    return state.model_copy(update={
        "status": "passed",
        "validation_status": "passed",
        "last_error": None,
    })


def _failed_state(state: ArtifactWorkflowState, error: str) -> ArtifactWorkflowState:
    return state.model_copy(update={"status": "failed", "last_error": error})


def _skip_state(state: ArtifactWorkflowState) -> ArtifactWorkflowState:
    return state.model_copy(update={
        "status": "skipped",
        "validation_status": "skipped",
        "judge_status": "skipped",
    })
