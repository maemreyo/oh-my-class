from __future__ import annotations

from dataclasses import dataclass
from typing import assert_never

from common.contracts.class_profile import ClassProfile, class_profile_from_class_info
from common.contracts.lesson_plan import LessonPlan, MethodologyMetadata
from common.contracts.lesson_sequence import BloomLevel, SessionPlan
from common.contracts.methodology_registry import MethodologyTag, methodology_entry_by_tag
from packages.agents.grounding import retrieve_grounding
from packages.agents.grounding.models import GroundingContext
from packages.agents.sub_agents.planner.lesson_consistency_validator import (
    LessonConsistencySeverity,
    LessonConsistencyValidator,
)
from packages.agents.sub_agents.planner.lesson_critic import CritiqueSeverity, critique_lesson
from packages.agents.sub_agents.unit_planner.mastery_planning import (
    MasteryDecision,
    MasterySignal,
    decide_mastery_action,
)

from packages.agents.sub_agents.planner.state import PlannerNodeState


@dataclass(frozen=True, slots=True)
class PlanningContext:
    topic: str
    profile: ClassProfile
    grounding: GroundingContext
    mastery_decision: MasteryDecision
    teacher_prior_minutes: int | None


def build_staged_lesson_plan(state: PlannerNodeState) -> LessonPlan:
    seed = state.get("seed")
    if seed is not None:
        return expand_seed_staged(SessionPlan.model_validate(seed), state)
    context = _planning_context(state)
    plan = _generate_plan(context)
    return _repair_until_clean(plan)


def expand_seed_staged(seed: SessionPlan, state: PlannerNodeState) -> LessonPlan:
    context = _planning_context(state, topic_override=seed.sub_topic)
    plan = LessonPlan(
        topic=seed.sub_topic,
        grade_level=context.profile.grade,
        subject=context.profile.subject_focus,
        duration_minutes=seed.duration_minutes,
        learning_objectives=[
            {
                "description": objective,
                "bloom_level": seed.bloom_level_primary,
                "assessment_method": "Seed-locked formative check",
            }
            for objective in seed.learning_objectives
        ],
        prerequisite_knowledge=[component.title for component in seed.knowledge_components],
        learning_plan=_gagne_plan(
            context=context,
            objectives=seed.learning_objectives,
            methodology=seed.methodology_primary,
            assessment_phrase=f"Check {seed.bloom_level_primary} mastery for {seed.sub_topic}.",
        ),
        assessment_checkpoints=[{
            "type": "exit_ticket",
            "description": "Seed-locked formative check: " + "; ".join(seed.learning_objectives),
            "trigger": "lesson_end",
        }],
        methodology=_methodology_metadata(seed.methodology_primary, context),
    )
    return _repair_until_clean(plan)


def _planning_context(state: PlannerNodeState, topic_override: str | None = None) -> PlanningContext:
    profile = _class_profile(state)
    topic = topic_override or _topic(state)
    grounding = retrieve_grounding(topic, profile.grade, profile.subject_focus, profile.language)
    mastery_decision = _mastery_decision(state)
    teacher_prior_minutes = _teacher_prior_minutes(state)
    return PlanningContext(
        topic=topic,
        profile=profile,
        grounding=grounding,
        mastery_decision=mastery_decision,
        teacher_prior_minutes=teacher_prior_minutes,
    )


def _class_profile(state: PlannerNodeState) -> ClassProfile:
    persona = state.get("persona_snapshot")
    if isinstance(persona, dict):
        return ClassProfile.model_validate(persona)
    return class_profile_from_class_info(dict(state.get("class_info", {})))


def _topic(state: PlannerNodeState) -> str:
    class_info = state.get("class_info", {})
    topic = class_info.get("topic") if isinstance(class_info, dict) else None
    if isinstance(topic, str) and topic.strip():
        return topic.strip()
    return state.get("raw_request", "Lesson").strip()


def _mastery_decision(state: PlannerNodeState) -> MasteryDecision:
    kt_mastery = state.get("kt_mastery")
    if not isinstance(kt_mastery, dict):
        return decide_mastery_action(None)
    first_value = next(iter(kt_mastery.values()), None)
    if not isinstance(first_value, dict):
        return decide_mastery_action(None)
    mastery = first_value.get("mastery")
    confidence = first_value.get("confidence")
    if not isinstance(mastery, int | float) or not isinstance(confidence, str):
        return decide_mastery_action(None)
    return decide_mastery_action(MasterySignal("lesson", float(mastery), confidence))


def _teacher_prior_minutes(state: PlannerNodeState) -> int | None:
    preferences = state.get("teacher_preferences")
    if not isinstance(preferences, dict):
        return None
    value = preferences.get("preferred_session_duration_minutes")
    if isinstance(value, int):
        return max(10, min(90, value))
    return None


def _generate_plan(context: PlanningContext) -> LessonPlan:
    objectives = _objectives(context)
    methodology = _methodology(context)
    assessment_phrase = "Assessment evidence first: students complete a checkpoint aligned to every objective."
    return LessonPlan(
        topic=context.topic,
        grade_level=context.profile.grade,
        subject=context.profile.subject_focus,
        duration_minutes=_duration(context),
        learning_objectives=objectives,
        prerequisite_knowledge=_prerequisites(context),
        learning_plan=_gagne_plan(
            context=context,
            objectives=[objective["description"] for objective in objectives],
            methodology=methodology,
            assessment_phrase=assessment_phrase,
        ),
        assessment_checkpoints=[
            {
                "type": "performance_task",
                "description": "Assess " + objective["description"],
                "trigger": "during_guided_practice",
            }
            for objective in objectives
        ],
        methodology=_methodology_metadata(methodology, context),
    )


def _objectives(context: PlanningContext) -> list[dict[str, str]]:
    levels = _bloom_levels(context)
    return [
        {
            "description": f"{_verb_for(level)} {context.topic}",
            "bloom_level": level,
            "assessment_method": f"Evidence task for {level} mastery",
        }
        for level in levels
    ]


def _bloom_levels(context: PlanningContext) -> tuple[BloomLevel, ...]:
    match context.profile.proficiency_level:
        case "advanced":
            return ("understand", "apply", "analyze")
        case "beginner":
            return ("remember", "understand", "apply")
        case "developing" | "proficient":
            pass
        case unreachable:
            assert_never(unreachable)
    match context.mastery_decision:
        case MasteryDecision.RETEACH:
            return ("remember", "understand", "apply")
        case MasteryDecision.PRACTICE | MasteryDecision.ASSUME:
            return ("understand", "apply", "analyze")
        case MasteryDecision.FALLBACK:
            return ("remember", "understand", "apply")
        case unreachable:
            assert_never(unreachable)


def _verb_for(level: BloomLevel) -> str:
    match level:
        case "remember":
            return "Recall core vocabulary for"
        case "understand":
            return "Explain the meaning of"
        case "apply":
            return "Apply procedures for"
        case "analyze":
            return "Analyze patterns in"
        case "evaluate":
            return "Evaluate strategies for"
        case "create":
            return "Create a model of"
        case unreachable:
            assert_never(unreachable)


def _prerequisites(context: PlanningContext) -> list[str]:
    prerequisites: list[str] = []
    if context.profile.prior_knowledge_gaps:
        prerequisites.extend(f"Reteach: {gap}" for gap in context.profile.prior_knowledge_gaps)
    match context.mastery_decision:
        case MasteryDecision.RETEACH:
            prerequisites.append(f"Reteach foundations for {context.topic}")
        case MasteryDecision.PRACTICE:
            prerequisites.append(f"Brief practice on foundations for {context.topic}")
        case MasteryDecision.ASSUME:
            prerequisites.append(f"Assume mastered foundations for {context.topic}")
        case MasteryDecision.FALLBACK:
            prerequisites.append(f"Grounding fallback prerequisites for {context.topic}")
        case unreachable:
            assert_never(unreachable)
    return prerequisites[:8]


def _duration(context: PlanningContext) -> int:
    if context.teacher_prior_minutes is not None:
        return context.teacher_prior_minutes
    if context.grounding.topic_norm is not None:
        return context.grounding.topic_norm.session_minutes_default
    if context.grounding.age_band is not None:
        return context.grounding.age_band.session_minutes_default
    match context.profile.attention_span_band:
        case "short":
            return 35
        case "medium":
            return 45
        case "long":
            return 60
        case unreachable:
            assert_never(unreachable)


def _methodology(context: PlanningContext) -> MethodologyTag:
    preferred = context.profile.learning_preferences.preferred_methodologies
    for value in preferred:
        match value:
            case "concept_map":
                return "concept_map"
            case "contrastive_pairs":
                return "contrastive_pairs"
            case "active_recall":
                return "active_recall"
            case "timed_quiz":
                return "timed_quiz"
            case "inverse_thinking":
                return "inverse_thinking"
            case _:
                continue
    match context.mastery_decision:
        case MasteryDecision.RETEACH:
            return "active_recall"
        case MasteryDecision.PRACTICE:
            return "timed_quiz"
        case MasteryDecision.ASSUME:
            return "concept_map"
        case MasteryDecision.FALLBACK:
            return "active_recall"
        case unreachable:
            assert_never(unreachable)


def _gagne_plan(
    *,
    context: PlanningContext,
    objectives: list[str],
    methodology: MethodologyTag,
    assessment_phrase: str,
) -> dict[str, str]:
    entry = methodology_entry_by_tag(methodology)
    required = ", ".join(entry.required_components)
    objectives_text = "; ".join(objectives)
    return {
        "gain_attention": f"Open with a misconception probe for {context.topic}.",
        "inform_objectives": objectives_text,
        "recall_prior": "; ".join(_prerequisites(context)),
        "present_content": f"Teach {context.topic} with {entry.label_en}; required components: {required}.",
        "provide_guidance": "Chunk examples to respect cognitive load and show one worked example at a time.",
        "elicit_performance": f"Students complete a {entry.label_en} task using {required}.",
        "provide_feedback": "Give criterion-based feedback tied to the assessment evidence.",
        "assess_performance": assessment_phrase,
        "enhance_retention": "End with retrieval practice and one transfer prompt for the next lesson.",
    }


def _methodology_metadata(methodology: MethodologyTag, context: PlanningContext) -> MethodologyMetadata:
    return MethodologyMetadata(
        tags=[methodology],
        target_skill_area=context.topic,
        student_profile_notes=_student_notes(context),
    )


def _student_notes(context: PlanningContext) -> str:
    return (
        f"profile={context.profile.proficiency_level}; "
        f"mastery={context.mastery_decision.value}; "
        f"grounding={context.grounding.grounding_status}"
    )


def _repair_until_clean(plan: LessonPlan) -> LessonPlan:
    validator = LessonConsistencyValidator()
    current = plan
    for _ in range(3):
        hard_issues = [issue for issue in validator.validate(current) if issue.severity is LessonConsistencySeverity.HARD]
        hard_critiques = [critique for critique in critique_lesson(current) if critique.severity is CritiqueSeverity.HARD]
        if not hard_issues and not hard_critiques:
            return current
        current = validator.repair(current)
    return current
