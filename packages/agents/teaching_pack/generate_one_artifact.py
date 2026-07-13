from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, NotRequired, TypedDict

from pydantic import ValidationError

from common.contracts.answer_set import AnswerSet, derive_answer_key_artifact, derive_answer_set
from common.contracts.artifact import ArtifactContent
from common.contracts.content_factory.orchestration import OrchestratorRequest, request_from_payload
from common.contracts.strategy_review import (
    SpecialistOutputDeclaration,
    enforce_content_brief_compliance,
)
from packages.agents.config.features import features
from packages.agents.sub_agents.content_creator.nodes import content_creator_node
from packages.agents.teaching_pack.specialist_capability import ANSWER_SET_ARTIFACT_TYPES
from packages.agents.teaching_pack.specialist_capability import (
    NATIVELY_DISPATCHED_ARTIFACT_TYPES as _NATIVELY_DISPATCHED_ARTIFACT_TYPES,
)
from packages.agents.teaching_pack.specialist_capability import (
    CapabilityResolution,
    family_for,
    resolve_specialist_capability,
)
from packages.agents.teaching_pack.specialist_depth import deepen_specialist_output
from packages.agents.teaching_pack.specialist_module import SpecialistRequest, get_specialist_module
from packages.agents.teaching_pack.specialist_registry import get_specialist
from packages.agents.teaching_pack.stages import StageEnum

if TYPE_CHECKING:
    from packages.agents.teaching_pack.content_orchestrator import ArtifactContentStore


class GenerateOneArtifactPayload(TypedDict):
    run_id: str
    artifact_generation_id: str
    artifact_type: str
    lesson_plan: dict[str, Any]
    research_brief: dict[str, Any]
    theme: str
    revision_feedback: NotRequired[str]
    dependency_artifact_references: NotRequired[list[dict[str, Any]]]
    subject: NotRequired[str]
    grade_band: NotRequired[str]
    content_brief: NotRequired[dict[str, Any]]
    tenant: NotRequired[dict[str, Any]]
    teacher_id: NotRequired[str]
    principal_id: NotRequired[str]
    principal_role: NotRequired[str]
    budget: NotRequired[dict[str, Any]]


class GenerateOneArtifactResult(TypedDict, total=False):
    artifact_references: list[dict[str, Any]]
    artifact_workflow_states: list[dict[str, Any]]


class ArtifactTypeMismatchError(ValueError):
    def __init__(self, expected: str, actual: str) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(f"expected {expected}, got {actual}")


class UnsupportedArtifactCapabilityError(ValueError):
    """Raised before an undeclared artifact can reach the generic creator."""

    def __init__(self, artifact_type: str, supported_alternatives: tuple[str, ...]) -> None:
        self.artifact_type = artifact_type
        self.supported_alternatives = supported_alternatives
        super().__init__(
            f"'{artifact_type}' has no registered specialist; supported artifact types: "
            + ", ".join(supported_alternatives),
        )


async def generate_one_artifact(
    payload: GenerateOneArtifactPayload,
    content_store: ArtifactContentStore | None = None,
) -> GenerateOneArtifactResult:
    artifact_type = payload["artifact_type"]
    generation_id = payload["artifact_generation_id"]
    # Resolve before parsing ContentBrief. An unknown type must fail with the
    # actionable capability error, not an incidental Pydantic Literal error.
    resolution = resolve_specialist_capability(
        artifact_type,
        generic_fallback_enabled=features().generic_content_creator_fallback_v1,
    )
    if resolution.status == "unsupported":
        return {
            "artifact_workflow_states": [_workflow_state(
                payload,
                "failed",
                UnsupportedArtifactCapabilityError(artifact_type, resolution.supported_alternatives),
            )],
        }
    try:
        request = request_from_payload(dict(payload))
        if content_store is not None and "tenant" in payload:
            from packages.agents.teaching_pack.tenant_scoped_content_store import (
                TenantScopedArtifactContentStore,
            )

            content_store = TenantScopedArtifactContentStore(content_store, request.tenant)
        dependency_artifacts: list[dict[str, Any]] = []
        dependency_answer_sets: dict[str, AnswerSet] = {}
        dependency_references = list(request.dependency_artifact_references)
        if content_store is not None:
            dependency_artifacts = [
                projection.model_dump(mode="json")
                for projection in await content_store.read_projections(dependency_references)
            ]
            for reference in dependency_references:
                document_id = reference.get("document_id")
                if not isinstance(document_id, str):
                    continue
                answer_set = await content_store.read_answer_set(document_id)
                if answer_set is not None:
                    dependency_answer_sets[document_id] = answer_set
        specialist = get_specialist(artifact_type)
        async with asyncio.timeout(request.budget.timeout_seconds):
            if artifact_type == "answer_key":
                artifact = _derived_answer_key(
                    dependency_artifacts,
                    dependency_references,
                    dependency_answer_sets,
                    request.theme,
                )
            elif artifact_type == "slide_deck":
                artifact = await _slide_deck_artifact(request, dependency_artifacts)
            elif specialist is not None:
                module = get_specialist_module(artifact_type)
                specialist_request = SpecialistRequest(
                    artifact_type=artifact_type,
                    lesson_plan=request.lesson_plan,
                    research_brief=request.research_brief,
                    content_brief=request.content_brief,
                )
                artifact = module.generate(specialist_request) if module is not None else specialist(
                    request.lesson_plan,
                    request.research_brief,
                )
                artifact["theme"] = request.theme
            else:
                result = await content_creator_node({
                    "lesson_plan": request.lesson_plan,
                    "research_bundle": request.research_brief,
                    "artifact_types": [artifact_type],
                    "theme": request.theme,
                    "run_id": request.run_id,
                    "current_step": StageEnum.ARTIFACT_WORKFLOW,
                    "artifacts": dependency_artifacts,
                    "revision_feedback": request.revision_feedback,
                    "use_hierarchical_creator": True,
                })
                artifact = _single_artifact(result)
        family = family_for(artifact_type)
        if family is not None and (
            specialist is not None or artifact_type in _NATIVELY_DISPATCHED_ARTIFACT_TYPES
        ):
            artifact = deepen_specialist_output(
                artifact,
                family=family,
                content_brief=request.content_brief,
                lesson_plan=request.lesson_plan,
                research_brief=request.research_brief,
            )
            _enforce_specialist_declaration(artifact, request)
        if str(artifact.get("artifact_type", "")) != artifact_type:
            raise ArtifactTypeMismatchError(artifact_type, str(artifact.get("artifact_type", "")))
        parsed = ArtifactContent.model_validate(artifact)
        artifact_id = str(artifact.get("artifact_id", f"{artifact_type}-1"))
    except (ArtifactTypeMismatchError, ValidationError, ValueError, TimeoutError) as exc:
        return {"artifact_workflow_states": [_workflow_state(payload, "failed", exc)]}
    projection = parsed.model_dump()
    answer_set: AnswerSet | None = None
    if artifact_type in ANSWER_SET_ARTIFACT_TYPES:
        answer_set = derive_answer_set(
            projection,
            source_document_id=f"{generation_id}:{artifact_id}",
            source_version=1,
        )
    _stamp_research_sources(projection, request.research_brief)
    _stamp_pedagogy_context(projection, request.lesson_plan)
    _stamp_specialist_lineage(projection, artifact_type, resolution)
    _stamp_orchestration_context(projection, request)
    if content_store is not None:
        from packages.agents.teaching_pack.content_orchestrator import ArtifactPersistenceResult

        persisted = ArtifactContent.model_validate(projection)
        dependency_document_ids = tuple(
            reference["document_id"]
            for reference in dependency_references
            if isinstance(reference.get("document_id"), str)
        ) if artifact_type == "answer_key" else ()
        reference = await content_store.persist_result(
            request.run_id,
            generation_id,
            ArtifactPersistenceResult(
                artifact=persisted,
                answer_set=answer_set,
                dependency_document_ids=dependency_document_ids,
            ),
            artifact_id,
        )
        return {
            "artifact_references": [reference.as_state()],
            "artifact_workflow_states": [_workflow_state(
                payload,
                "passed",
                None,
                artifact_id=artifact_id,
            )],
        }
    return {
        "artifact_workflow_states": [_workflow_state(
            payload,
            "passed",
            None,
            artifact_id=artifact_id,
        )],
    }


def _enforce_specialist_declaration(artifact: dict[str, Any], request: OrchestratorRequest) -> None:
    metadata = artifact.get("metadata")
    declaration = metadata.get("specialist_output_declaration") if isinstance(metadata, dict) else None
    if not isinstance(declaration, dict):
        raise ValueError("specialist output omitted specialist_output_declaration")
    produced = SpecialistOutputDeclaration.model_validate(declaration)
    enforce_content_brief_compliance(request.content_brief, produced)


def _stamp_orchestration_context(chunk: dict[str, Any], request: OrchestratorRequest) -> None:
    metadata = dict(chunk.get("metadata") or {})
    metadata.setdefault("content_brief_id", request.content_brief.content_brief_id)
    metadata.setdefault("knowledge_db_version", request.content_brief.knowledge_db_version)
    metadata.setdefault("organization_id", request.tenant.organization_id)
    metadata.setdefault("tenant_audit_fingerprint", request.tenant.audit_fingerprint)
    metadata.setdefault("generation_budget", request.budget.model_dump(mode="json"))
    chunk["metadata"] = metadata


def _stamp_research_sources(chunk: dict[str, Any], research_brief: dict[str, Any]) -> None:
    sources = research_brief.get("sources")
    if not isinstance(sources, list):
        return
    corpus: list[dict[str, str]] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        excerpt = source.get("excerpt")
        if not isinstance(excerpt, str) or not excerpt:
            continue
        entry: dict[str, str] = {"title": str(source.get("title", "")), "content": excerpt}
        url = source.get("url")
        if isinstance(url, str) and url:
            entry["url"] = url
        corpus.append(entry)
    if not corpus:
        return
    metadata = dict(chunk.get("metadata") or {})
    metadata.setdefault("research_sources", corpus)
    chunk["metadata"] = metadata


def _stamp_pedagogy_context(chunk: dict[str, Any], lesson_plan: dict[str, Any]) -> None:
    context: dict[str, Any] = {}
    objectives = lesson_plan.get("learning_objectives")
    if isinstance(objectives, list) and objectives:
        context["learning_objectives"] = objectives
    for key in ("grade", "grade_level"):
        value = lesson_plan.get(key)
        if isinstance(value, (int, str)):
            context[key] = value
            break
    if not context:
        return
    metadata = dict(chunk.get("metadata") or {})
    metadata.setdefault("pedagogy_context", context)
    chunk["metadata"] = metadata


def _stamp_specialist_lineage(
    chunk: dict[str, Any],
    artifact_type: str,
    resolution: CapabilityResolution,
) -> None:
    module = get_specialist_module(artifact_type)
    if module is None:
        return
    lineage = module.lineage(resolution)
    metadata = dict(chunk.get("metadata") or {})
    metadata.setdefault("specialist_lineage", {
        "artifact_type": lineage.artifact_type,
        "specialist_id": lineage.specialist_id,
        "module_version": lineage.module_version,
        "consumed_content_brief_fields": list(lineage.consumed_content_brief_fields),
    })
    chunk["metadata"] = metadata


def _single_artifact(result: dict[str, Any]) -> dict[str, Any]:
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 1:
        raise ValueError("content_creator_node must return exactly one artifact")
    artifact = artifacts[0]
    if not isinstance(artifact, dict):
        raise ValueError("content_creator_node returned a non-object artifact")
    return artifact


def _derived_answer_key(
    dependencies: list[dict[str, Any]],
    references: list[dict[str, Any]],
    answer_sets: dict[str, AnswerSet],
    theme: str,
) -> dict[str, Any]:
    quiz_index = next((index for index, artifact in enumerate(dependencies) if artifact.get("artifact_type") == "quiz"), None)
    if quiz_index is None:
        raise ValueError("answer_key requires a generated quiz dependency")
    quiz = dependencies[quiz_index]
    document_id = references[quiz_index].get("document_id") if quiz_index < len(references) else None
    answer_set = answer_sets.get(document_id) if isinstance(document_id, str) else None
    if answer_set is None:
        raise ValueError("quiz dependency has no teacher-only answer set")
    language = str(quiz.get("accessibility", {}).get("language", "vi")) if isinstance(
        quiz.get("accessibility"), dict,
    ) else "vi"
    return derive_answer_key_artifact(quiz, answer_set, theme=theme, language=language)


async def _slide_deck_artifact(
    request: OrchestratorRequest,
    dependencies: list[dict[str, Any]],
) -> dict[str, Any]:
    from packages.agents.sub_agents.content_creator.slide_deck_artifact import build_slide_deck_artifact

    return await build_slide_deck_artifact({
        "lesson_plan": request.lesson_plan,
        "research_bundle": request.research_brief,
        "theme": request.theme,
        "run_id": request.run_id,
        "artifacts": dependencies,
        "revision_feedback": request.revision_feedback,
    })


def _workflow_state(
    payload: GenerateOneArtifactPayload,
    status: str,
    error: Exception | None,
    artifact_id: str | None = None,
) -> dict[str, Any]:
    artifact_type = payload["artifact_type"]
    state: dict[str, Any] = {
        "workflow_id": f"{payload['artifact_generation_id']}:{artifact_type}",
        "artifact_generation_id": payload["artifact_generation_id"],
        "artifact_id": artifact_id or artifact_type,
        "artifact_type": artifact_type,
        "status": status,
    }
    if error is not None:
        state["error_class"] = type(error).__name__
        state["error_summary"] = str(error)[:240]
    return state
