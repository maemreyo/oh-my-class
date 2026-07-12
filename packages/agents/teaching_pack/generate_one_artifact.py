from __future__ import annotations

from typing import TYPE_CHECKING, Any, NotRequired, TypedDict

from pydantic import ValidationError

from common.contracts.answer_set import AnswerSet, derive_answer_key_artifact, derive_answer_set
from common.contracts.artifact import ArtifactContent
from packages.agents.config.features import features
from packages.agents.sub_agents.content_creator.nodes import content_creator_node
from packages.agents.teaching_pack.specialist_capability import (
    ANSWER_SET_ARTIFACT_TYPES,
)
from packages.agents.teaching_pack.specialist_capability import (
    NATIVELY_DISPATCHED_ARTIFACT_TYPES as _NATIVELY_DISPATCHED_ARTIFACT_TYPES,
)
from packages.agents.teaching_pack.specialist_capability import (
    CapabilityResolution,
    resolve_specialist_capability,
)
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
    # #464: threaded through by artifact_fanout.py's `_payload` so a caller
    # can resolve `content_coverage_resolution.resolve_content_coverage`
    # (subject/grade-band-scoped curriculum coverage, not just per-artifact-
    # type code capability). `NotRequired` since not every caller of this
    # payload (e.g. existing tests) supplies them yet.
    subject: NotRequired[str]
    grade_band: NotRequired[str]


# #464: ADR-053 names this "OrchestratorRequest" -- an alias, not a parallel
# type. Graph state stays a plain dict (LangGraph checkpoint requirement),
# so this remains a TypedDict rather than a Pydantic model.
OrchestratorRequest = GenerateOneArtifactPayload


class GenerateOneArtifactResult(TypedDict, total=False):
    artifact_references: list[dict[str, Any]]
    artifact_workflow_states: list[dict[str, Any]]


class ArtifactTypeMismatchError(ValueError):
    def __init__(self, expected: str, actual: str) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(f"expected {expected}, got {actual}")


class UnsupportedArtifactCapabilityError(ValueError):
    """#464: raised instead of silently reaching the generic content-creator
    fallback for an artifact type with no registered specialist and no native
    dispatch branch. Fails closed before any LLM call; names the artifact
    types the teacher can actually pick instead."""

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
    try:
        dependency_artifacts: list[dict[str, Any]] = []
        dependency_answer_sets: dict[str, AnswerSet] = {}
        dependency_references = payload.get("dependency_artifact_references", [])
        if content_store is not None:
            dependency_artifacts = [
                projection.model_dump(mode="json")
                for projection in await content_store.read_projections(
                    dependency_references,
                )
            ]
            for reference in dependency_references:
                document_id = reference.get("document_id")
                if not isinstance(document_id, str):
                    continue
                answer_set = await content_store.read_answer_set(document_id)
                if answer_set is not None:
                    dependency_answer_sets[document_id] = answer_set
        resolution = resolve_specialist_capability(
            artifact_type,
            generic_fallback_enabled=features().generic_content_creator_fallback_v1,
        )
        specialist = get_specialist(artifact_type)
        if resolution.status == "unsupported":
            raise UnsupportedArtifactCapabilityError(artifact_type, resolution.supported_alternatives)
        if artifact_type == "answer_key":
            artifact = _derived_answer_key(dependency_artifacts, dependency_references, dependency_answer_sets, payload["theme"])
        elif artifact_type == "slide_deck":
            artifact = await _slide_deck_artifact(payload, dependency_artifacts)
        elif specialist is not None:
            module = get_specialist_module(artifact_type)
            request = SpecialistRequest(
                artifact_type=artifact_type,
                lesson_plan=payload["lesson_plan"],
                research_brief=payload["research_brief"],
            )
            # #464: dispatch through the typed SpecialistModule wrapper
            # (SpecialistRequest in, declaration/lineage available) rather
            # than calling the raw registry callable positionally -- falls
            # back to the raw callable only if the registry and the module
            # registry have somehow diverged (guarded by a registry-matrix
            # test in test_specialist_module.py; should never happen).
            artifact = module.generate(request) if module is not None else specialist(
                payload["lesson_plan"], payload["research_brief"],
            )
            artifact["theme"] = payload["theme"]
        else:
            result = await content_creator_node({
                "lesson_plan": payload["lesson_plan"],
                "research_bundle": payload["research_brief"],
                "artifact_types": [artifact_type],
                "theme": payload["theme"],
                "run_id": payload["run_id"],
                "current_step": StageEnum.ARTIFACT_WORKFLOW,
                "artifacts": dependency_artifacts,
                "revision_feedback": payload.get("revision_feedback", ""),
                "use_hierarchical_creator": True,
            })
            artifact = _single_artifact(result)
        if str(artifact.get("artifact_type", "")) != artifact_type:
            raise ArtifactTypeMismatchError(artifact_type, str(artifact.get("artifact_type", "")))
        parsed = ArtifactContent.model_validate(artifact)
        artifact_id = str(artifact.get("artifact_id", f"{artifact_type}-1"))
    except (ArtifactTypeMismatchError, ValidationError, ValueError) as exc:
        return {"artifact_workflow_states": [_workflow_state(payload, "failed", exc)]}
    projection = parsed.model_dump()
    answer_set: AnswerSet | None = None
    if artifact_type in ANSWER_SET_ARTIFACT_TYPES:
        answer_set = derive_answer_set(
            projection,
            source_document_id=f"{generation_id}:{artifact_id}",
            source_version=1,
        )
    _stamp_research_sources(projection, payload["research_brief"])
    _stamp_pedagogy_context(projection, payload["lesson_plan"])
    _stamp_specialist_lineage(projection, artifact_type, resolution)
    if content_store is not None:
        from packages.agents.teaching_pack.content_orchestrator import ArtifactPersistenceResult

        persisted = ArtifactContent.model_validate(projection)
        dependency_document_ids = tuple(
            reference["document_id"]
            for reference in dependency_references
            if isinstance(reference.get("document_id"), str)
        ) if artifact_type == "answer_key" else ()
        reference = await content_store.persist_result(
            payload["run_id"],
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


def _stamp_research_sources(chunk: dict[str, Any], research_brief: dict[str, Any]) -> None:
    """Attach the run's grounded research corpus to the artifact metadata.

    This closes the researcher -> Layer-2 fact_check seam: the gate reads
    ``artifact.metadata.research_sources`` and cross-references factual claims against
    the source bodies. Only sources with a fetched ``excerpt`` (real content) are
    carried — content-less sources are useless to fact_check. Fail-open: never
    overwrite an existing ``research_sources`` and never add an empty list.
    """
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
    """Attach a leakage-safe lesson-plan subset for the Layer-2 pedagogical check.

    Only the learning objectives and target grade are carried — the fields the
    pedagogical alignment/Bloom/readability checks need. Teacher scripts, answer keys,
    and other plan internals are deliberately excluded. Without this the gate had no
    lesson_plan and those metrics silently auto-passed. Fail-open and non-destructive.
    """
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
    """Attach the ADR-053 `SpecialistLineage` provenance record -- which
    module (specialist_id), at which version, generated this artifact, and
    which `ContentBrief` fields it declares it consumed (`()` today; see
    `specialist_module.py`'s module docstring). Fail-open like the other
    stamps: an unknown artifact_type (should be unreachable past capability
    resolution) leaves metadata untouched rather than raising here.
    """
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
    payload: GenerateOneArtifactPayload,
    dependencies: list[dict[str, Any]],
) -> dict[str, Any]:
    from packages.agents.sub_agents.content_creator.slide_deck_artifact import build_slide_deck_artifact

    return await build_slide_deck_artifact({
        "lesson_plan": payload["lesson_plan"],
        "research_bundle": payload["research_brief"],
        "theme": payload["theme"],
        "run_id": payload["run_id"],
        "artifacts": dependencies,
        "revision_feedback": payload.get("revision_feedback", ""),
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
