"""Family-specific deterministic depth applied at the specialist boundary.

Existing specialist generators remain small and renderer-compatible.  This
adapter owns the deeper contracts shared across a whole specialist family:
instructional phase plans, assessment blueprints/progression, evidence-aware
synthesis plans, and presentation lineage.  It runs before schema validation
and persistence, so the production path cannot bypass these invariants.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from common.contracts.content_brief import ContentBrief
from common.contracts.content_factory.assessment import build_item_blueprints, validate_question_card
from common.contracts.content_factory.instructional_design import build_instructional_design_plan
from common.contracts.content_factory.synthesis import (
    build_synthesis_plan,
    prerequisite_order,
    visual_semantics,
)
from packages.agents.teaching_pack.specialist_capability import SpecialistFamily

JsonObject = dict[str, Any]


def deepen_specialist_output(
    artifact: JsonObject,
    *,
    family: SpecialistFamily,
    content_brief: ContentBrief,
    lesson_plan: JsonObject,
    research_brief: JsonObject,
) -> JsonObject:
    deepened = deepcopy(artifact)
    metadata = _metadata(deepened)
    metadata["content_brief_id"] = content_brief.content_brief_id
    metadata["knowledge_db_version"] = content_brief.knowledge_db_version
    metadata["objective_lineage"] = _objective_lineage(lesson_plan, content_brief)
    metadata["approved_objective_ids"] = [entry["objective_id"] for entry in metadata["objective_lineage"]]
    metadata["source_citation_ids"] = list(content_brief.source_citation_ids)
    metadata["specialist_output_declaration"] = {
        "methodology": content_brief.methodology,
        "objectives_covered": list(content_brief.objectives),
        "learning_moves_used": list(content_brief.learning_moves),
    }
    match family:
        case "lesson_design":
            _deepen_lesson(deepened, lesson_plan)
        case "assessment":
            _deepen_assessment(deepened, lesson_plan, practice=False)
        case "practice":
            _deepen_assessment(deepened, lesson_plan, practice=True)
        case "synthesis":
            _deepen_synthesis(deepened, lesson_plan, research_brief)
        case "presentation":
            _deepen_presentation(deepened, lesson_plan, content_brief)
    return deepened


def _deepen_lesson(artifact: JsonObject, lesson_plan: JsonObject) -> None:
    plan = build_instructional_design_plan(lesson_plan)
    metadata = _metadata(artifact)
    metadata["instructional_design_plan"] = plan.model_dump(mode="json")
    sections = artifact.get("sections")
    if not isinstance(sections, list):
        return
    by_id = {str(section.get("id")): section for section in sections if isinstance(section, dict)}
    for phase in plan.phases:
        target = by_id.get(phase.phase_id)
        if target is None:
            target = {"id": phase.phase_id, "title": phase.title, "content": phase.teacher_actions[0]}
            sections.append(target)
        target["objective_ids"] = list(phase.objective_ids)
        target["timebox_minutes"] = phase.timebox_minutes
        target["teacher_actions"] = list(phase.teacher_actions)
        target["student_actions"] = list(phase.student_actions)
        target["materials"] = list(phase.materials)
        target["checks_for_understanding"] = list(phase.checks_for_understanding)
        target["anticipated_responses"] = list(phase.anticipated_responses)
        target["misconception_responses"] = list(phase.misconception_responses)
        target["differentiation"] = list(phase.differentiation)
        target["transition"] = phase.transition
        target["closure"] = phase.closure


def _deepen_assessment(artifact: JsonObject, lesson_plan: JsonObject, *, practice: bool) -> None:
    cards = _question_cards(artifact)
    if practice and len(cards) < 6:
        cards = _practice_cards(lesson_plan)
        _replace_question_cards(artifact, cards)
    if not cards:
        return
    response_type = "selected_response" if all(
        isinstance(card.get("options"), dict)
        and card.get("answer") in card.get("options", {})
        and len([value for value in card.get("options", {}).values() if str(value).strip()]) >= 2
        for card in cards
    ) else "constructed_response"
    blueprints = build_item_blueprints(
        lesson_plan,
        count=len(cards),
        response_type=response_type,
        practice=practice,
    )
    for card, blueprint in zip(cards, blueprints, strict=True):
        card["blueprint_id"] = blueprint.item_id
        card["objective_id"] = blueprint.objective_id
        card["knowledge_component_id"] = blueprint.knowledge_component_id
        card["cognitive_demand"] = blueprint.cognitive_demand
        card["difficulty"] = blueprint.difficulty
        card["misconception_target_id"] = str(card.get("misconception_id") or blueprint.misconception_target_id)
        card["evidence_statement_id"] = blueprint.evidence_statement_id
        card["verification_method"] = blueprint.verification_method
        if blueprint.practice_stage is not None:
            card["practice_stage"] = blueprint.practice_stage
        if blueprint.verification_method == "solver":
            card["verification"] = {
                "method": "deterministic_solver",
                "trace": str(card.get("explain") or "solver-generated subject capability item"),
            }
        validate_question_card(card, blueprint)
    metadata = _metadata(artifact)
    metadata["item_blueprints"] = [blueprint.model_dump(mode="json") for blueprint in blueprints]
    if practice:
        metadata["practice_progression"] = [
            blueprint.practice_stage for blueprint in blueprints if blueprint.practice_stage is not None
        ]
    metadata["verification_summary"] = {
        "solver": sum(blueprint.verification_method == "solver" for blueprint in blueprints),
        "declared_answer": sum(blueprint.verification_method == "declared_answer" for blueprint in blueprints),
        "rubric": sum(blueprint.verification_method == "rubric" for blueprint in blueprints),
        "teacher_review": sum(blueprint.verification_method == "teacher_review" for blueprint in blueprints),
    }


def _deepen_synthesis(artifact: JsonObject, lesson_plan: JsonObject, research_brief: JsonObject) -> None:
    artifact_type = str(artifact.get("artifact_type") or "synthesis")
    target = 180 if artifact_type == "reading_passage" else 90
    plan = build_synthesis_plan(lesson_plan, research_brief, target_length_words=target)
    metadata = _metadata(artifact)
    metadata["synthesis_plan"] = plan.model_dump(mode="json")
    metadata["claim_evidence_map"] = {
        claim.claim_id: list(claim.evidence_ids) for claim in plan.retained_claims
    }
    if artifact_type == "reading_passage":
        retained_text = " ".join(claim.text for claim in plan.retained_claims)
        sections = artifact.get("sections")
        if isinstance(sections, list) and sections and isinstance(sections[0], dict):
            sections[0]["content"] = retained_text
        metadata["passage_sources"] = [
            evidence_id for claim in plan.retained_claims for evidence_id in claim.evidence_ids
        ]
    elif artifact_type == "roadmap":
        order = _prerequisite_order(lesson_plan)
        metadata["prerequisite_order"] = list(order)
        _reorder_roadmap_sections(artifact, order)
    elif artifact_type == "infographic":
        semantics = visual_semantics(plan)
        metadata["visual_semantics"] = list(semantics)
        accessibility = artifact.setdefault("accessibility", {})
        if isinstance(accessibility, dict):
            accessibility["alt_texts"] = [str(item["alt_text"]) for item in semantics]
            accessibility["long_descriptions"] = [str(item["long_description"]) for item in semantics]
            accessibility["grayscale_safe"] = True
            accessibility["no_image_fallback"] = [str(item["no_image_fallback"]) for item in semantics]


def _deepen_presentation(artifact: JsonObject, lesson_plan: JsonObject, content_brief: ContentBrief) -> None:
    metadata = _metadata(artifact)
    metadata["presentation_plan"] = {
        "objective_ids": [entry["objective_id"] for entry in _objective_lineage(lesson_plan, content_brief)],
        "methodology": content_brief.methodology,
        "required_moves": list(content_brief.learning_moves),
        "accessibility": {
            "speaker_notes_separate": True,
            "color_not_sole_signal": True,
            "print_safe": True,
        },
    }


def _practice_cards(lesson_plan: JsonObject) -> list[JsonObject]:
    objectives = _objective_records(lesson_plan)
    stages = ("worked_example", "guided", "independent", "retrieval", "interleaved", "transfer")
    prompts = {
        "worked_example": "Study the worked reasoning, then identify the decisive step",
        "guided": "Complete the next step using the provided scaffold",
        "independent": "Solve independently and justify the choice",
        "retrieval": "Recall the idea without looking back at the example",
        "interleaved": "Choose when this idea applies among mixed cases",
        "transfer": "Apply the idea in a new context and explain what stays invariant",
    }
    cards: list[JsonObject] = []
    for index, stage in enumerate(stages, start=1):
        objective_id, objective = objectives[(index - 1) % len(objectives)]
        cards.append({
            "type": "question_card",
            "id": f"practice-{stage}-{index}",
            "text": f"{prompts[stage]}: {objective}",
            "options": {
                "A": "Write or select the response supported by the lesson evidence.",
                "B": "",
                "C": "",
                "D": "",
            },
            "answer": objective,
            "explain": "Teacher reference only; the student projection removes this field.",
            "objective_id": objective_id,
        })
    return cards


def _question_cards(artifact: JsonObject) -> list[JsonObject]:
    cards: list[JsonObject] = []
    sections = artifact.get("sections")
    if not isinstance(sections, list):
        return cards
    for section in sections:
        if not isinstance(section, dict):
            continue
        components = section.get("components")
        if not isinstance(components, list):
            continue
        cards.extend(component for component in components if isinstance(component, dict) and component.get("type") == "question_card")
    return cards


def _replace_question_cards(artifact: JsonObject, cards: list[JsonObject]) -> None:
    sections = artifact.get("sections")
    if not isinstance(sections, list) or not sections or not isinstance(sections[0], dict):
        artifact["sections"] = [{"id": "practice", "title": "Practice progression", "components": cards}]
        return
    sections[0]["components"] = cards
    sections[0]["title"] = "Practice progression"


def _metadata(artifact: JsonObject) -> JsonObject:
    metadata = artifact.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
        artifact["metadata"] = metadata
    return metadata


def _objective_records(lesson_plan: JsonObject) -> list[tuple[str, str]]:
    raw = lesson_plan.get("learning_objectives")
    records: list[tuple[str, str]] = []
    if not isinstance(raw, list):
        return [("objective-1", "Demonstrate the approved learning objective.")]
    for index, item in enumerate(raw, start=1):
        if isinstance(item, str) and item.strip():
            records.append((f"objective-{index}", item.strip()))
        elif isinstance(item, dict):
            description = item.get("description")
            if isinstance(description, str) and description.strip():
                objective_id = item.get("objective_id")
                records.append((
                    objective_id.strip() if isinstance(objective_id, str) and objective_id.strip() else f"objective-{index}",
                    description.strip(),
                ))
    return records or [("objective-1", "Demonstrate the approved learning objective.")]


def _objective_lineage(lesson_plan: JsonObject, content_brief: ContentBrief) -> list[JsonObject]:
    records = _objective_records(lesson_plan)
    return [
        {
            "objective_id": objective_id,
            "description": description,
            "content_brief_id": content_brief.content_brief_id,
        }
        for objective_id, description in records
    ]


def _prerequisite_order(lesson_plan: JsonObject) -> tuple[str, ...]:
    records = _objective_records(lesson_plan)
    ids = [objective_id for objective_id, _description in records]
    raw_edges = lesson_plan.get("prerequisite_edges")
    edges: list[tuple[str, str]] = []
    if isinstance(raw_edges, list):
        for edge in raw_edges:
            if isinstance(edge, dict):
                prerequisite = edge.get("prerequisite_id") or edge.get("source")
                dependent = edge.get("dependent_id") or edge.get("target")
                if isinstance(prerequisite, str) and isinstance(dependent, str):
                    edges.append((prerequisite, dependent))
            elif isinstance(edge, (list, tuple)) and len(edge) == 2:
                edges.append((str(edge[0]), str(edge[1])))
    return prerequisite_order(ids, edges)


def _reorder_roadmap_sections(artifact: JsonObject, order: tuple[str, ...]) -> None:
    sections = artifact.get("sections")
    if not isinstance(sections, list):
        return
    by_objective: dict[str, JsonObject] = {}
    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            continue
        objective_id = str(section.get("objective_id") or f"objective-{index + 1}")
        section["objective_id"] = objective_id
        section["prerequisite_ids"] = list(order[: order.index(objective_id)]) if objective_id in order else []
        by_objective[objective_id] = section
    reordered = [by_objective[objective_id] for objective_id in order if objective_id in by_objective]
    reordered.extend(section for section in sections if isinstance(section, dict) and section not in reordered)
    artifact["sections"] = reordered
