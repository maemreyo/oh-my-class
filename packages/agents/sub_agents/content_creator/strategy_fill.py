from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, assert_never

from packages.agents.sub_agents.content_creator.state import ContentCreatorNodeState
from packages.agents.sub_agents.content_creator.strategy_lineage import with_strategy_lineage

ArtifactKind = Literal[
    "lesson", "worksheet", "quiz", "drill", "recap", "infographic",
    "flashcard_deck", "answer_key", "roadmap",
]


@dataclass(frozen=True, slots=True)
class StrategyFillContext:
    artifact_type: ArtifactKind
    section_id: str
    lesson_plan: dict[str, Any]
    state: ContentCreatorNodeState
    fact: str


@dataclass(frozen=True, slots=True)
class StrategyFillResult:
    components: list[dict[str, Any]]
    slot_ids: list[str]
    fallbacks: list[dict[str, str]]


def selected_strategy_components(context: StrategyFillContext) -> StrategyFillResult:
    slots = _slots_for_section(context)
    components: list[dict[str, Any]] = []
    slot_ids: list[str] = []
    fallbacks: list[dict[str, str]] = []
    for slot in slots:
        component = _component_for_slot(context, slot)
        slot_id = str(slot.get("slot_id", ""))
        slot_ids.append(slot_id)
        components.append(component)
        if component["type"] == "callout":
            fallbacks.append({
                "slot_id": slot_id,
                "original_move_id": str(slot.get("learning_move_id", "")),
                "attempted_component": str(slot.get("component_type", "")),
                "reason": "unsupported_component_type",
            })
    return StrategyFillResult(components=components, slot_ids=slot_ids, fallbacks=fallbacks)


def strategy_metadata(result: StrategyFillResult) -> dict[str, Any]:
    if not result.slot_ids and not result.fallbacks:
        return {}
    return {
        "strategy_slot_ids": [*result.slot_ids],
        "strategy_fallbacks": [*result.fallbacks],
    }


def artifact_strategy_metadata(sections: list[dict[str, Any]]) -> dict[str, Any]:
    slot_ids: list[str] = []
    fallbacks: list[dict[str, str]] = []
    for section in sections:
        metadata = section.get("metadata")
        if not isinstance(metadata, dict):
            continue
        ids = metadata.get("strategy_slot_ids")
        if isinstance(ids, list):
            slot_ids.extend(str(slot_id) for slot_id in ids)
        section_fallbacks = metadata.get("strategy_fallbacks")
        if isinstance(section_fallbacks, list):
            fallbacks.extend(item for item in section_fallbacks if isinstance(item, dict))
    return {"slot_ids": [*dict.fromkeys(slot_ids)], "fallbacks": fallbacks}


def _slots_for_section(context: StrategyFillContext) -> list[dict[str, Any]]:
    if context.section_id != _target_section(context.artifact_type):
        return []
    plan = context.state.get("component_strategy_plan")
    if not isinstance(plan, dict):
        return []
    recommended = _object(plan.get("recommended"))
    slot_by_id = {
        str(slot.get("slot_id")): slot
        for slot in _dicts(recommended.get("learning_sequence"))
    }
    ordered_ids = _ordered_slot_ids(context.artifact_type, recommended)
    return [
        slot_by_id[slot_id]
        for slot_id in ordered_ids
        if slot_id in slot_by_id and context.artifact_type in _strings(slot_by_id[slot_id].get("target_artifacts"))
    ]


def _ordered_slot_ids(artifact_type: ArtifactKind, recommended: dict[str, Any]) -> list[str]:
    for projection in _dicts(recommended.get("artifact_strategies")):
        if projection.get("artifact_type") == artifact_type:
            return _strings(projection.get("ordered_slot_ids"))
    return []


def _target_section(artifact_type: ArtifactKind) -> str:
    match artifact_type:
        case "quiz":
            return "assessment"
        case "lesson" | "worksheet" | "drill":
            return "guided_practice"
        case "recap" | "infographic" | "roadmap":
            return "present_content"
        case "flashcard_deck":
            return "cards"
        case "answer_key":
            return "teacher_only_answers"
        case unreachable:
            assert_never(unreachable)


def _component_for_slot(context: StrategyFillContext, slot: dict[str, Any]) -> dict[str, Any]:
    component_type = str(slot.get("component_type", ""))
    match component_type:
        case "vocab_cluster":
            return with_strategy_lineage(slot, _vocab_cluster(context, slot))
        case "contrastive_pairs":
            return with_strategy_lineage(slot, _contrastive_pairs(context, slot))
        case "question_list":
            return with_strategy_lineage(slot, _question_list(context, slot))
        case "flow_step":
            return with_strategy_lineage(slot, _flow_step(context, slot))
        case "active_recall_prompt":
            return with_strategy_lineage(slot, _active_recall_prompt(context, slot))
        case _:
            return with_strategy_lineage(slot, {
                "type": "callout",
                "variant": "warning",
                "title": "Strategy component fallback",
                "body": f"Could not fill {component_type}; use guided teacher review before export.",
            })


def _vocab_cluster(context: StrategyFillContext, slot: dict[str, Any]) -> dict[str, Any]:
    topic = _topic(context.lesson_plan)
    return {
        "type": "vocab_cluster",
        "title": f"Key vocabulary for {topic}",
        "description": "; ".join(_strings(slot.get("fill_requirements"))) or context.fact,
        "items": [
            {"word": topic, "definition": context.fact, "example": _objective(context.lesson_plan)},
        ],
        "discrimination_prompt": "Use each term in a sentence that shows its precise meaning.",
    }


def _contrastive_pairs(context: StrategyFillContext, slot: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "contrastive_pairs",
        "title": "Do not confuse these ideas",
        "rows": [{
            "terms": _topic(context.lesson_plan),
            "distinction": "; ".join(_strings(slot.get("fill_requirements"))) or context.fact,
        }],
    }


def _question_list(context: StrategyFillContext, slot: dict[str, Any]) -> dict[str, Any]:
    count = _max_item_count(slot)
    questions = [
        {
            "type": "question_card",
            "id": f"{slot.get('slot_id', 'slot')}-{index}",
            "text": f"Which statement best supports: {_objective(context.lesson_plan)}?",
            "options": {"A": context.fact, "B": "A related but incomplete idea", "C": "An unrelated detail", "D": "A contradicted claim"},
            "answer": "A",
            "explain": "The selected option is grounded in the verified research finding.",
            "group": "a",
        }
        for index in range(1, count + 1)
    ]
    return {
        "type": "question_list",
        "questions": questions,
        "section_key": context.section_id,
        "group": "a",
        "title": "Strategy-aligned assessment",
        "instruction": "Answer using the lesson model, not guessing.",
    }


def _flow_step(context: StrategyFillContext, slot: dict[str, Any]) -> dict[str, Any]:
    requirements = _strings(slot.get("fill_requirements")) or [context.fact]
    return {
        "type": "flow_step",
        "steps": [
            {"time": f"{index * 3} min", "title": requirement, "body": context.fact}
            for index, requirement in enumerate(requirements, start=1)
        ],
    }


def _active_recall_prompt(context: StrategyFillContext, slot: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "active_recall_prompt",
        "instruction": f"Without notes, explain {_objective(context.lesson_plan)}.",
        "time_minutes": min(_max_time_minutes(slot), 30),
        "scaffold_hint": context.fact,
    }


def _max_item_count(slot: dict[str, Any]) -> int:
    budget = _object(slot.get("budget"))
    value = budget.get("max_item_count")
    if isinstance(value, int):
        return max(1, min(value, 5))
    return 1


def _max_time_minutes(slot: dict[str, Any]) -> int:
    budget = _object(slot.get("budget"))
    value = budget.get("max_time_minutes")
    if isinstance(value, int):
        return max(1, value)
    return 3


def _objective(lesson_plan: dict[str, Any]) -> str:
    objectives = lesson_plan.get("learning_objectives")
    for objective in _dicts(objectives):
        description = objective.get("description")
        if isinstance(description, str) and description:
            return description
    return _topic(lesson_plan)


def _topic(lesson_plan: dict[str, Any]) -> str:
    topic = lesson_plan.get("topic")
    if isinstance(topic, str) and topic:
        return topic
    return "the lesson topic"


def _object(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _dicts(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]
