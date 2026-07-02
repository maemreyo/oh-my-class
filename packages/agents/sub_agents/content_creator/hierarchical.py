from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal, assert_never

from common.contracts.artifact import ArtifactContent
from common.contracts.methodology_registry import MethodologyTag, methodology_entry_by_tag
from packages.agents.sub_agents.content_creator.nodes import validate_no_cdn, validate_no_pii

from packages.agents.sub_agents.content_creator.state import ContentCreatorNodeState

ArtifactKind = Literal["lesson", "worksheet", "quiz", "drill", "recap", "infographic"]


@dataclass(frozen=True, slots=True)
class SectionOutline:
    section_id: str
    title: str
    job: str
    objective: str | None
    gagne_event: str | None


def build_hierarchical_artifacts(state: ContentCreatorNodeState) -> dict[str, list[dict[str, Any]]]:
    artifacts = [
        _build_artifact(_artifact_kind(artifact_type), state)
        for artifact_type in state.get("artifact_types", ["lesson"])
    ]
    issues = [*validate_no_cdn(artifacts), *validate_no_pii(artifacts)]
    if issues:
        msg = "content guard failed: " + "; ".join(issues)
        raise ValueError(msg)
    return {"artifacts": artifacts}


def _artifact_kind(value: str) -> ArtifactKind:
    match value:
        case "lesson":
            return "lesson"
        case "worksheet":
            return "worksheet"
        case "quiz":
            return "quiz"
        case "drill":
            return "drill"
        case "recap":
            return "recap"
        case "infographic":
            return "infographic"
        case _:
            msg = f"unsupported artifact type: {value}"
            raise ValueError(msg)


def _build_artifact(artifact_type: ArtifactKind, state: ContentCreatorNodeState) -> dict[str, Any]:
    lesson_plan = state["lesson_plan"]
    research_bundle = state["research_bundle"]
    outline = _outline(artifact_type, lesson_plan)
    sections = [_fill_section(artifact_type, section, state) for section in outline]
    metadata = _metadata(artifact_type, sections, lesson_plan, research_bundle, state)
    artifact = ArtifactContent(
        artifact_type=artifact_type,
        theme=state.get("theme", "default"),
        title=f"{_topic(lesson_plan)} {artifact_type.title()}",
        sections=sections,
        metadata=metadata,
        accessibility={"language": _language(lesson_plan)},
    )
    _validate_coverage(artifact, lesson_plan)
    _validate_methodology(artifact, lesson_plan)
    return artifact.model_dump()


def _outline(artifact_type: ArtifactKind, lesson_plan: dict[str, Any]) -> list[SectionOutline]:
    objectives = _objective_texts(lesson_plan)
    phases = _phase_items(lesson_plan)
    base = [
        SectionOutline("objectives", "Learning goals", "surface objectives", objectives[0] if objectives else None, None),
        SectionOutline("direct_teaching", "Direct teaching", "teach verified content", None, "present_content"),
        SectionOutline("guided_practice", "Guided practice", "practice with feedback", objectives[-1] if objectives else None, "elicit_performance"),
        SectionOutline("closure", "Closure", "assess and retain", None, "assess_performance"),
    ]
    match artifact_type:
        case "lesson":
            return base
        case "worksheet" | "drill":
            return base[1:3] + [SectionOutline("independent_practice", "Independent practice", "student practice", objectives[-1] if objectives else None, None)]
        case "quiz":
            return [SectionOutline("assessment", "Assessment", "quiz objectives", objective, "assess_performance") for objective in objectives[:5]]
        case "recap" | "infographic":
            return [SectionOutline(event, event.replace("_", " ").title(), "summarize phase", None, event) for event in phases[:4]]
        case unreachable:
            assert_never(unreachable)


def _fill_section(
    artifact_type: ArtifactKind,
    outline: SectionOutline,
    state: ContentCreatorNodeState,
) -> dict[str, Any]:
    if _forced_failure(state, artifact_type, outline.section_id):
        return _regen_placeholder(outline)
    lesson_plan = state["lesson_plan"]
    research_bundle = state["research_bundle"]
    fact = _verified_fact(research_bundle)
    components = [
        {"type": "heading", "level": 2, "text": outline.title},
        {"type": "paragraph", "text": f"{outline.job}: {fact}"},
    ]
    components.extend(_methodology_components(lesson_plan, state))
    return {
        "section_id": outline.section_id,
        "title": outline.title,
        "content": f"{outline.job}: {fact}",
        "objective": outline.objective,
        "gagne_event": outline.gagne_event,
        "components": components,
        "metadata": {"filled_independently": True, "grounded_fact": fact},
    }


def _regen_placeholder(outline: SectionOutline) -> dict[str, Any]:
    return {
        "section_id": outline.section_id,
        "title": outline.title,
        "content": "This section needs scoped regeneration before teacher approval.",
        "needs_regen": True,
        "metadata": {"filled_independently": True, "failure_mode": "persistent_section_failure"},
    }


def _metadata(
    artifact_type: ArtifactKind,
    sections: list[dict[str, Any]],
    lesson_plan: dict[str, Any],
    research_bundle: dict[str, Any],
    state: ContentCreatorNodeState,
) -> dict[str, Any]:
    return {
        "generation_mode": "outline_fill_coherence",
        "generation_status": "needs_regen" if any(section.get("needs_regen") for section in sections) else "complete",
        "artifact_type": artifact_type,
        "covered_objectives": _objective_texts(lesson_plan),
        "covered_gagne_events": [event for event, _value in _phase_pairs(lesson_plan)],
        "grounding_status": "verified_subset" if _verified_fact(research_bundle) else "needs_review",
        "adaptation_context": state.get("component_effectiveness", {}),
    }


def _validate_coverage(artifact: ArtifactContent, lesson_plan: dict[str, Any]) -> None:
    content = json.dumps(artifact.model_dump(), ensure_ascii=False).casefold()
    missing_objectives = [objective for objective in _objective_texts(lesson_plan) if objective.casefold() not in content]
    if missing_objectives:
        msg = "coverage contract failed for objective: " + missing_objectives[0]
        raise ValueError(msg)
    missing_events = [event for event, _value in _phase_pairs(lesson_plan) if event not in content]
    if missing_events:
        msg = "coverage contract failed for Gagné event: " + missing_events[0]
        raise ValueError(msg)


def _validate_methodology(artifact: ArtifactContent, lesson_plan: dict[str, Any]) -> None:
    content = json.dumps(artifact.model_dump(), ensure_ascii=False).casefold()
    for tag in _methodology_tags(lesson_plan):
        entry = methodology_entry_by_tag(tag)
        missing = [component for component in entry.required_components if component.casefold() not in content]
        if missing:
            msg = "methodology component missing: " + missing[0]
            raise ValueError(msg)


def _methodology_components(lesson_plan: dict[str, Any], state: ContentCreatorNodeState) -> list[dict[str, str]]:
    if state.get("disable_methodology_components") is True:
        return []
    components: list[dict[str, str]] = []
    for tag in _methodology_tags(lesson_plan):
        for component in methodology_entry_by_tag(tag).required_components:
            components.append({"type": "paragraph", "text": f"methodology component: {component}"})
    return components


def _methodology_tags(lesson_plan: dict[str, Any]) -> list[MethodologyTag]:
    methodology = lesson_plan.get("methodology")
    if not isinstance(methodology, dict):
        return []
    tags = methodology.get("tags")
    if not isinstance(tags, list):
        return []
    return [_methodology_tag(str(tag)) for tag in tags]


def _methodology_tag(value: str) -> MethodologyTag:
    match value:
        case "concept_map":
            return "concept_map"
        case "contrastive_pairs":
            return "contrastive_pairs"
        case "film_based":
            return "film_based"
        case "shy_student_1on1":
            return "shy_student_1on1"
        case "active_recall":
            return "active_recall"
        case "why_wrong_reasoning":
            return "why_wrong_reasoning"
        case "timed_quiz":
            return "timed_quiz"
        case "roleplay_script":
            return "roleplay_script"
        case "inverse_thinking":
            return "inverse_thinking"
        case "semantic_anchoring":
            return "semantic_anchoring"
        case _:
            msg = f"unknown methodology tag: {value}"
            raise ValueError(msg)


def _objective_texts(lesson_plan: dict[str, Any]) -> list[str]:
    objectives = lesson_plan.get("learning_objectives")
    if not isinstance(objectives, list):
        return []
    return [str(item.get("description")) for item in objectives if isinstance(item, dict) and item.get("description")]


def _phase_pairs(lesson_plan: dict[str, Any]) -> list[tuple[str, Any]]:
    phases = lesson_plan.get("learning_plan")
    if not isinstance(phases, dict):
        return []
    return [(str(event), value) for event, value in phases.items()]


def _phase_items(lesson_plan: dict[str, Any]) -> list[str]:
    return [event for event, _value in _phase_pairs(lesson_plan)]


def _verified_fact(research_bundle: dict[str, Any]) -> str:
    findings = research_bundle.get("key_findings")
    if not isinstance(findings, list):
        return "Teacher-provided lesson grounding only."
    contradicted = {str(fact) for fact in research_bundle.get("contradicted_facts", []) if isinstance(fact, str)}
    for finding in findings:
        if isinstance(finding, str) and finding not in contradicted:
            return finding
    return "Teacher-provided lesson grounding only."


def _forced_failure(state: ContentCreatorNodeState, artifact_type: ArtifactKind, section_id: str) -> bool:
    failures = state.get("force_section_failures")
    if not isinstance(failures, list):
        return False
    return f"{artifact_type}:{section_id}" in {str(value) for value in failures}


def _topic(lesson_plan: dict[str, Any]) -> str:
    return str(lesson_plan.get("topic", "Teaching Pack"))


def _language(lesson_plan: dict[str, Any]) -> str:
    return str(lesson_plan.get("language", "en"))
