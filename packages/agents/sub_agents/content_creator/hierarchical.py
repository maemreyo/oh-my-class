from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal, assert_never

from common.contracts.artifact import ArtifactContent
from packages.agents.sub_agents.content_creator.hierarchical_sections import flashcards, regen_placeholder
from packages.agents.sub_agents.content_creator.methodology_helpers import methodology_components, validate_methodology
from packages.agents.sub_agents.content_creator.strategy_fill import (
    StrategyFillContext,
    artifact_strategy_metadata,
    selected_strategy_components,
    strategy_metadata,
)
from packages.agents.sub_agents.content_creator.nodes import validate_no_cdn, validate_no_pii
from packages.agents.sub_agents.content_creator.slide_deck_artifact import build_slide_deck_artifact

from packages.agents.sub_agents.content_creator.state import ContentCreatorNodeState

ArtifactKind = Literal[
    "lesson", "worksheet", "quiz", "drill", "recap", "infographic",
    "flashcard_deck", "answer_key", "roadmap", "slide_deck",
]


@dataclass(frozen=True, slots=True)
class SectionOutline:
    section_id: str
    title: str
    job: str
    objective: str | None
    gagne_event: str | None


async def build_hierarchical_artifacts(state: ContentCreatorNodeState) -> dict[str, list[dict[str, Any]]]:
    artifacts = [
        await _build_artifact(_artifact_kind(artifact_type), state)
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
        case "flashcard_deck":
            return "flashcard_deck"
        case "answer_key":
            return "answer_key"
        case "roadmap":
            return "roadmap"
        case "slide_deck":
            return "slide_deck"
        case _:
            msg = f"unsupported artifact type: {value}"
            raise ValueError(msg)


async def _build_artifact(artifact_type: ArtifactKind, state: ContentCreatorNodeState) -> dict[str, Any]:
    if artifact_type == "slide_deck":
        return build_slide_deck_artifact(state)
    lesson_plan = state["lesson_plan"]
    research_bundle = state["research_bundle"]
    outline = _outline(artifact_type, lesson_plan)
    prose_by_section = await _generate_section_prose(artifact_type, outline, lesson_plan, research_bundle, state)
    sections = [_fill_section(artifact_type, section, state, prose_by_section) for section in outline]
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
    validate_methodology(artifact, lesson_plan)
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
        case "recap" | "infographic" | "roadmap":
            return [SectionOutline(event, event.replace("_", " ").title(), "summarize phase", None, event) for event in phases[:4]]
        case "flashcard_deck":
            return [SectionOutline("cards", "Flashcards", "build active-recall cards", objectives[0] if objectives else None, "enhance_retention")]
        case "answer_key":
            return [SectionOutline("teacher_only_answers", "Teacher-only answer key", "explain correct answers", objective, "assess_performance") for objective in objectives[:5]]
        case "slide_deck":
            return [SectionOutline("deck", "Slide deck", "present visual sequence", objectives[0] if objectives else None, "present_content")]
        case unreachable:
            assert_never(unreachable)


def _fill_section(
    artifact_type: ArtifactKind,
    outline: SectionOutline,
    state: ContentCreatorNodeState,
    prose_by_section: dict[str, str],
) -> dict[str, Any]:
    if _forced_failure(state, artifact_type, outline.section_id):
        return regen_placeholder(outline.section_id, outline.title)
    lesson_plan = state["lesson_plan"]
    research_bundle = state["research_bundle"]
    fact = _verified_fact(research_bundle)
    prose = prose_by_section.get(outline.section_id) or f"{outline.job}: {fact}"
    components = [
        {"type": "heading", "level": 2, "text": outline.title},
        {"type": "paragraph", "text": prose},
    ]
    strategy_fill = selected_strategy_components(StrategyFillContext(
        artifact_type=artifact_type,
        section_id=outline.section_id,
        lesson_plan=lesson_plan,
        state=state,
        fact=fact,
    ))
    components.extend(strategy_fill.components)
    components.extend(methodology_components(lesson_plan, state))
    section = {
        "section_id": outline.section_id,
        "title": outline.title,
        "content": prose,
        "objective": outline.objective,
        "gagne_event": outline.gagne_event,
        "components": components,
        "metadata": {
            "filled_independently": True,
            "grounded_fact": fact,
            **strategy_metadata(strategy_fill),
        },
    }
    if artifact_type == "answer_key":
        section["teacher_only"] = True
    if artifact_type == "flashcard_deck":
        section["cards"] = flashcards(lesson_plan, fact)
    return section


async def _generate_section_prose(
    artifact_type: ArtifactKind,
    outline: list[SectionOutline],
    lesson_plan: dict[str, Any],
    research_bundle: dict[str, Any],
    state: ContentCreatorNodeState,
) -> dict[str, str]:
    """One LLM call per artifact: writes grounded prose for every section at once."""
    if not outline:
        return {}
    fact = _verified_fact(research_bundle)
    sections_brief = [
        {
            "section_id": section.section_id,
            "title": section.title,
            "job": section.job,
            "objective": section.objective,
            "gagne_event": section.gagne_event,
        }
        for section in outline
    ]

    from packages.agents.config.models import MODELS
    from packages.agents.llm import extract_json_text
    from packages.agents.runtime import AgentRuntime, AgentRuntimeConfig
    from packages.agents.teaching_pack.stages import StageEnum, stage_number

    system_prompt = (
        "You are an expert K-12 teaching content writer. Write one short, clear, "
        "age-appropriate paragraph per section of a teaching artifact, grounded "
        "ONLY in the given fact — do not invent new facts or numbers.\n\n"
        'Respond ONLY with a JSON object: {"<section_id>": "<paragraph>", ...}, '
        "one entry per section given. No prose, no explanation, no markdown fences."
    )
    user_prompt = (
        f"Artifact type: {artifact_type}\nTopic: {_topic(lesson_plan)}\n"
        f"Grounded fact: {fact}\n\n"
        f"Sections:\n{json.dumps(sections_brief, ensure_ascii=False, indent=2)}"
    )
    run_id = str(state.get("run_id", ""))
    current_step = state.get("current_step", StageEnum.ARTIFACT_WORKFLOW)
    runtime = AgentRuntime(AgentRuntimeConfig(
        agent="content_creator",
        run_id=run_id,
        step=stage_number(current_step),
        step_label=getattr(current_step, "value", str(current_step)),
        model=MODELS.content_creator,
        base_temperature=0.4,
        retry_temperature=0.2,
    ))
    messages = runtime.messages(system_prompt, user_prompt)

    def parse(content: str) -> dict[str, str]:
        data = json.loads(extract_json_text(content))
        if not isinstance(data, dict):
            raise ValueError("expected a JSON object mapping section_id to prose")
        return {str(key): str(value) for key, value in data.items()}

    return await runtime.complete_json_with_retries(
        messages=messages,
        parse=parse,
        retry_messages=lambda _err, _content: runtime.messages(
            system_prompt,
            "Invalid response. Return ONLY the JSON object mapping section_id to prose.",
        ),
        extra_tags=(f"artifact:{artifact_type}",),
    )


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
        "covered_bloom_levels": _bloom_levels(lesson_plan),
        "covered_gagne_events": [event for event, _value in _phase_pairs(lesson_plan)],
        "grounding_status": "verified_subset" if _verified_fact(research_bundle) else "needs_review",
        "adaptation_context": state.get("component_effectiveness", {}),
        "component_strategy": artifact_strategy_metadata(sections),
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


def _objective_texts(lesson_plan: dict[str, Any]) -> list[str]:
    objectives = lesson_plan.get("learning_objectives")
    if not isinstance(objectives, list):
        return []
    return [str(item.get("description")) for item in objectives if isinstance(item, dict) and item.get("description")]


def _bloom_levels(lesson_plan: dict[str, Any]) -> list[str]:
    objectives = lesson_plan.get("learning_objectives")
    if not isinstance(objectives, list):
        return []
    levels: list[str] = []
    for item in objectives:
        if not isinstance(item, dict):
            continue
        level = item.get("bloom_level")
        if isinstance(level, str) and level not in levels:
            levels.append(level)
    return levels


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
