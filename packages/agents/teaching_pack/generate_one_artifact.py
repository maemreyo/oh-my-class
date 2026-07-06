from __future__ import annotations

from typing import Any, NotRequired, TypedDict

from pydantic import ValidationError

from common.contracts.artifact import ArtifactContent

from packages.agents.sub_agents.content_creator.nodes import content_creator_node
from packages.agents.teaching_pack.stages import StageEnum


class GenerateOneArtifactPayload(TypedDict):
    run_id: str
    artifact_generation_id: str
    artifact_type: str
    lesson_plan: dict[str, Any]
    research_brief: dict[str, Any]
    theme: str
    revision_feedback: NotRequired[str]
    dependency_artifacts: NotRequired[list[dict[str, Any]]]


class GenerateOneArtifactResult(TypedDict, total=False):
    artifact_chunks: list[dict[str, Any]]
    artifact_workflow_states: list[dict[str, Any]]


class ArtifactTypeMismatchError(ValueError):
    def __init__(self, expected: str, actual: str) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(f"expected {expected}, got {actual}")


async def generate_one_artifact(payload: GenerateOneArtifactPayload) -> GenerateOneArtifactResult:
    artifact_type = payload["artifact_type"]
    generation_id = payload["artifact_generation_id"]
    try:
        result = await content_creator_node({
            "lesson_plan": payload["lesson_plan"],
            "research_bundle": payload["research_brief"],
            "artifact_types": [artifact_type],
            "theme": payload["theme"],
            "run_id": payload["run_id"],
            "current_step": StageEnum.ARTIFACT_WORKFLOW,
            "artifacts": payload.get("dependency_artifacts", []),
            "revision_feedback": payload.get("revision_feedback", ""),
            "use_hierarchical_creator": artifact_type == "slide_deck",
        })
        artifact = _single_artifact(result)
        if str(artifact.get("artifact_type", "")) != artifact_type:
            raise ArtifactTypeMismatchError(artifact_type, str(artifact.get("artifact_type", "")))
        parsed = ArtifactContent.model_validate(artifact).model_dump()
        artifact_id = str(artifact.get("artifact_id", f"{artifact_type}-1"))
    except (ArtifactTypeMismatchError, ValidationError, ValueError) as exc:
        return {"artifact_workflow_states": [_workflow_state(payload, "failed", exc)]}
    chunk = {**parsed, "artifact_id": artifact_id, "artifact_generation_id": generation_id}
    _stamp_research_sources(chunk, payload["research_brief"])
    _stamp_pedagogy_context(chunk, payload["lesson_plan"])
    return {
        "artifact_chunks": [chunk],
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
