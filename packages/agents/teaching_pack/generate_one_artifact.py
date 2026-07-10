from __future__ import annotations

from typing import TYPE_CHECKING, Any, NotRequired, TypedDict

from pydantic import ValidationError

from common.contracts.answer_set import AnswerSet, derive_answer_key_artifact, derive_answer_set
from common.contracts.artifact import ArtifactContent
from packages.agents.sub_agents.content_creator.nodes import content_creator_node
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


class GenerateOneArtifactResult(TypedDict, total=False):
    artifact_references: list[dict[str, Any]]
    artifact_workflow_states: list[dict[str, Any]]


class ArtifactTypeMismatchError(ValueError):
    def __init__(self, expected: str, actual: str) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(f"expected {expected}, got {actual}")


async def generate_one_artifact(
    payload: GenerateOneArtifactPayload,
    content_store: ArtifactContentStore | None = None,
) -> GenerateOneArtifactResult:
    artifact_type = payload["artifact_type"]
    generation_id = payload["artifact_generation_id"]
    try:
        dependency_artifacts: list[dict[str, Any]] = []
        if content_store is not None:
            dependency_artifacts = [
                projection.model_dump(mode="json")
                for projection in await content_store.read_projections(
                    payload.get("dependency_artifact_references", []),
                )
            ]
        specialist = get_specialist(artifact_type)
        if artifact_type == "answer_key":
            artifact = _derived_answer_key(dependency_artifacts, payload["theme"])
        elif artifact_type == "slide_deck":
            artifact = await _slide_deck_artifact(payload, dependency_artifacts)
        elif specialist is not None:
            artifact = specialist(payload["lesson_plan"], payload["research_brief"])
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
    if artifact_type in {"quiz", "drill", "exit_ticket"}:
        answer_set = derive_answer_set(
            projection,
            source_document_id=f"{generation_id}:{artifact_id}",
            source_version=1,
        )
        projection["metadata"] = {
            **projection["metadata"],
            "answer_set": answer_set.model_dump(mode="json"),
        }
    _stamp_research_sources(projection, payload["research_brief"])
    _stamp_pedagogy_context(projection, payload["lesson_plan"])
    if content_store is not None:
        persisted = ArtifactContent.model_validate(projection)
        reference = await content_store.persist(
            payload["run_id"],
            generation_id,
            persisted,
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


def _single_artifact(result: dict[str, Any]) -> dict[str, Any]:
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 1:
        raise ValueError("content_creator_node must return exactly one artifact")
    artifact = artifacts[0]
    if not isinstance(artifact, dict):
        raise ValueError("content_creator_node returned a non-object artifact")
    return artifact


def _derived_answer_key(dependencies: list[dict[str, Any]], theme: str) -> dict[str, Any]:
    quiz = next((artifact for artifact in dependencies if artifact.get("artifact_type") == "quiz"), None)
    if quiz is None:
        raise ValueError("answer_key requires a generated quiz dependency")
    metadata = quiz.get("metadata")
    answer_set_json = metadata.get("answer_set") if isinstance(metadata, dict) else None
    if not isinstance(answer_set_json, dict):
        raise ValueError("quiz dependency has no teacher-only answer set")
    answer_set = AnswerSet.model_validate(answer_set_json)
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
