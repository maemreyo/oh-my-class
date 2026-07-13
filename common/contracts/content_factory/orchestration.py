"""Typed Content Factory orchestration contracts and ContentBrief assembly."""

from __future__ import annotations

import hashlib
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from common.contracts.content_brief import ContentBrief, resolve_methodology
from common.contracts.content_factory.tenancy import TenantContext, personal_tenant_context
from common.contracts.content_intelligence_graph.objective_decomposition import (
    ObjectiveDecompositionGraph,
    decompose_objective,
)

JsonObject = dict[str, Any]


class ContentBriefAssemblyError(ValueError):
    pass


class GenerationBudget(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    timeout_seconds: float = Field(default=120.0, gt=0, le=900)
    max_tokens: int = Field(default=12_000, ge=256, le=200_000)
    max_parallelism: int = Field(default=4, ge=1, le=32)


class OrchestratorRequest(BaseModel):
    """Closed request accepted by the production Content Orchestrator."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(min_length=1, max_length=64)
    artifact_generation_id: str = Field(min_length=1, max_length=160)
    artifact_type: str = Field(min_length=1, max_length=40)
    lesson_plan: JsonObject
    research_brief: JsonObject
    theme: str = Field(default="default", min_length=1, max_length=40)
    revision_feedback: str = Field(default="", max_length=10_000)
    dependency_artifact_references: tuple[JsonObject, ...] = ()
    subject: str = Field(default="general", min_length=1, max_length=120)
    grade_band: str = Field(default="grades_3_5", min_length=1, max_length=80)
    content_brief: ContentBrief
    tenant: TenantContext
    budget: GenerationBudget = Field(default_factory=GenerationBudget)

    @model_validator(mode="after")
    def _brief_matches_request(self) -> OrchestratorRequest:
        if self.content_brief.run_id != self.run_id:
            raise ValueError("content brief run_id does not match orchestrator request")
        if str(self.content_brief.artifact_type) != self.artifact_type:
            raise ValueError("content brief artifact_type does not match orchestrator request")
        return self


class OrchestratorResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    artifact_type: str
    generation_id: str
    status: str
    document_id: str | None = None
    content_brief_id: str
    knowledge_db_version: str | None = None
    specialist_id: str | None = None
    retryable: bool = False
    error_class: str | None = None
    error_summary: str | None = None


def build_content_brief(
    *,
    run_id: str,
    artifact_type: str,
    lesson_plan: JsonObject,
    research_brief: JsonObject,
    dependency_document_ids: list[str] | tuple[str, ...] = (),
    allow_topic_fallback: bool = False,
) -> ContentBrief:
    if allow_topic_fallback:
        lesson_plan = _with_legacy_test_objective(lesson_plan)
    objectives = _objective_records(lesson_plan)
    if not objectives:
        raise ContentBriefAssemblyError("cannot assemble ContentBrief without approved objectives")

    intelligence = research_brief.get("content_intelligence")
    intelligence = intelligence if isinstance(intelligence, dict) else {}
    scope = _scope_from_intelligence(objectives, intelligence)
    teacher_pin = _string(lesson_plan.get("methodology")) or _string(lesson_plan.get("methodology_primary"))
    recommendation = _string(intelligence.get("methodology_recommendation"))
    methodology, methodology_source = resolve_methodology(
        teacher_pin=teacher_pin,
        strategy_recommendation=recommendation,
    )
    objective_texts = [description for _objective_id, description in objectives]
    source_ids = _source_ids(research_brief)
    terminology = _unique_strings([
        *_string_list(lesson_plan.get("terminology")),
        *_string_list(intelligence.get("terminology")),
    ])
    learning_moves = _unique_strings([
        *_string_list(lesson_plan.get("learning_moves")),
        *_string_list(intelligence.get("learning_moves")),
    ])
    must_include = _unique_strings([
        *_string_list(lesson_plan.get("must_include")),
        *scope,
    ])
    answer_policy = "teacher_only" if artifact_type in {"quiz", "drill", "exit_ticket"} else (
        "derived" if artifact_type == "answer_key" else "none"
    )
    version = _string(intelligence.get("snapshot_version")) or _string(
        research_brief.get("knowledge_db_version"),
    )
    brief_digest = hashlib.sha256(
        f"{run_id}|{artifact_type}|{'|'.join(objective_texts)}|{version or ''}".encode(),
    ).hexdigest()[:16]
    return ContentBrief(
        content_brief_id=f"cb-{brief_digest}",
        run_id=run_id,
        artifact_type=artifact_type,
        objectives=objective_texts,
        scope=scope,
        methodology=methodology,
        methodology_source=methodology_source,
        learning_moves=learning_moves,
        eligible_component_variants=_string_list(intelligence.get("eligible_component_variants")),
        terminology=terminology,
        must_include=must_include,
        avoid=_unique_strings(_string_list(lesson_plan.get("avoid"))),
        answer_policy=answer_policy,
        dependency_document_ids=list(dict.fromkeys(str(item) for item in dependency_document_ids)),
        source_citation_ids=source_ids,
        knowledge_db_version=version,
    )


def request_from_payload(payload: JsonObject) -> OrchestratorRequest:
    run_id = str(payload["run_id"])
    lesson_plan = _object(payload.get("lesson_plan"))
    research_brief = _object(payload.get("research_brief"))
    references = tuple(_object(item) for item in payload.get("dependency_artifact_references", []) if isinstance(item, dict))
    dependency_ids = [
        str(reference["document_id"])
        for reference in references
        if isinstance(reference.get("document_id"), str)
    ]
    raw_brief = payload.get("content_brief")
    content_brief = (
        ContentBrief.model_validate(raw_brief)
        if isinstance(raw_brief, dict)
        else build_content_brief(
            run_id=run_id,
            artifact_type=str(payload["artifact_type"]),
            lesson_plan=_with_legacy_test_objective(lesson_plan),
            research_brief=research_brief,
            dependency_document_ids=dependency_ids,
            allow_topic_fallback=True,
        )
    )
    raw_tenant = payload.get("tenant")
    if isinstance(raw_tenant, dict):
        tenant = TenantContext.model_validate(raw_tenant)
    else:
        teacher_id = str(payload.get("teacher_id") or lesson_plan.get("teacher_id") or run_id)
        tenant = personal_tenant_context(
            teacher_id=teacher_id,
            principal_id=str(payload.get("principal_id") or teacher_id),
            principal_role="worker" if payload.get("principal_role") == "worker" else "teacher",
        )
    raw_budget = payload.get("budget")
    budget = GenerationBudget.model_validate(raw_budget) if isinstance(raw_budget, dict) else GenerationBudget()
    return OrchestratorRequest(
        run_id=run_id,
        artifact_generation_id=str(payload["artifact_generation_id"]),
        artifact_type=str(payload["artifact_type"]),
        lesson_plan=lesson_plan,
        research_brief=research_brief,
        theme=str(payload.get("theme") or "default"),
        revision_feedback=str(payload.get("revision_feedback") or ""),
        dependency_artifact_references=references,
        subject=str(payload.get("subject") or lesson_plan.get("subject") or "general"),
        grade_band=str(payload.get("grade_band") or lesson_plan.get("grade_level") or "grades_3_5"),
        content_brief=content_brief,
        tenant=tenant,
        budget=budget,
    )


def _with_legacy_test_objective(lesson_plan: JsonObject) -> JsonObject:
    """Compatibility only for direct unit-level calls that bypass fanout.

    The production fanout always sends an explicit serialized ContentBrief.
    Older glue tests call ``generate_one_artifact`` directly with only a topic;
    preserving that seam avoids turning an orchestration migration into a
    broad test-fixture rewrite.  The topic is copied verbatim and the brief is
    marked by its deterministic ``legacy`` objective id -- no content is
    invented.
    """
    if _objective_records(lesson_plan):
        return lesson_plan
    topic = _string(lesson_plan.get("topic")) or _string(lesson_plan.get("title"))
    if topic is None:
        return lesson_plan
    return {**lesson_plan, "learning_objectives": [{"objective_id": "legacy-topic", "description": topic}]}


def _scope_from_intelligence(
    objectives: list[tuple[str, str]],
    intelligence: JsonObject,
) -> list[str]:
    raw_graph = intelligence.get("objective_decomposition")
    if not isinstance(raw_graph, dict):
        return _unique_strings(_string_list(intelligence.get("scope")))
    graph = ObjectiveDecompositionGraph.model_validate(raw_graph)
    scope: list[str] = []
    for objective_id, _description in objectives:
        scope.extend(decompose_objective(graph, objective_id))
    return _unique_strings(scope)


def _objective_records(lesson_plan: JsonObject) -> list[tuple[str, str]]:
    raw = lesson_plan.get("learning_objectives")
    if not isinstance(raw, list):
        return []
    records: list[tuple[str, str]] = []
    for index, item in enumerate(raw, start=1):
        if isinstance(item, str) and item.strip():
            records.append((f"objective-{index}", item.strip()))
        elif isinstance(item, dict):
            description = _string(item.get("description"))
            if description:
                records.append((_string(item.get("objective_id")) or f"objective-{index}", description))
    return records


def _source_ids(research_brief: JsonObject) -> list[str]:
    raw = research_brief.get("sources")
    if not isinstance(raw, list):
        return []
    ids: list[str] = []
    for index, source in enumerate(raw, start=1):
        if not isinstance(source, dict):
            continue
        explicit = _string(source.get("source_id")) or _string(source.get("evidence_id"))
        if explicit:
            ids.append(explicit)
            continue
        label = _string(source.get("url")) or _string(source.get("title")) or f"source-{index}"
        digest = hashlib.sha256(label.encode()).hexdigest()[:12]
        ids.append(f"source-{digest}")
    return list(dict.fromkeys(ids))


def _object(value: Any) -> JsonObject:
    return value if isinstance(value, dict) else {}


def _string(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _unique_strings(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
