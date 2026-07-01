from __future__ import annotations

from dataclasses import dataclass
from typing import Any, assert_never

from common.contracts.class_profile import ClassProfile, class_profile_from_class_info
from common.contracts.lesson_sequence import (
    BloomLevel,
    GroundingStatus,
    KnowledgeComponent,
    LessonSequence,
    SessionPlan,
)
from common.contracts.methodology_registry import MethodologyTag
from packages.agents.middleware.sequence_consistency_validator import (
    ConsistencySeverity,
    SequenceConsistencyValidator,
)

from packages.agents.sub_agents.unit_planner.state import UnitPlannerNodeState


@dataclass(frozen=True, slots=True)
class ClarificationRequiredError(Exception):
    questions: tuple[str, ...]

    def __str__(self) -> str:
        return "CLARIFICATION_REQUIRED: " + "; ".join(self.questions)


async def unit_planner_node(state: UnitPlannerNodeState) -> dict[str, Any]:
    class_profile = _class_profile(state)
    grounding_status = _grounding_status(state.get("grounding"))
    topic = _topic(state)
    if grounding_status == "ungrounded" and _is_ambiguous(topic):
        raise ClarificationRequiredError(("Please clarify the exact unit topic or curriculum target.",))

    sequence = _build_sequence(topic, class_profile, grounding_status)
    sequence = _apply_soft_priors(sequence, state)
    repaired = _repair_sequence(sequence)
    return {"lesson_sequence": repaired.model_dump(mode="json")}


def _class_profile(state: UnitPlannerNodeState) -> ClassProfile:
    persona = state.get("persona_snapshot")
    if isinstance(persona, dict):
        return ClassProfile.model_validate(persona)
    return class_profile_from_class_info(dict(state.get("class_info", {})))


def _topic(state: UnitPlannerNodeState) -> str:
    class_info = state.get("class_info", {})
    topic = class_info.get("topic") if isinstance(class_info, dict) else None
    if isinstance(topic, str) and topic.strip():
        return topic.strip()
    request = state.get("raw_request", "")
    return request.strip()


def _grounding_status(grounding: dict[str, Any] | None) -> GroundingStatus:
    if not grounding:
        return "ungrounded"
    value = grounding.get("grounding_status", grounding.get("status", "partial"))
    match value:
        case "grounded":
            return "grounded"
        case "partial":
            return "partial"
        case "ungrounded":
            return "ungrounded"
        case _:
            return "partial"


def _is_ambiguous(topic: str) -> bool:
    words = [word for word in topic.replace("—", " ").split() if word]
    return len(words) < 2 or topic.casefold() in {"math", "science", "english", "lesson", "unit"}


def _build_sequence(
    topic: str,
    profile: ClassProfile,
    grounding_status: GroundingStatus,
) -> LessonSequence:
    session_count = _session_count(profile)
    duration = _session_duration(profile)
    bloom_levels = _bloom_levels(session_count, profile)
    sessions = [
        _session(topic, index + 1, duration, bloom_levels[index], profile)
        for index in range(session_count)
    ]
    total_duration = sum(session.duration_minutes for session in sessions)
    return LessonSequence(
        topic=topic,
        grade_level=profile.grade,
        subject=profile.subject_focus,
        locale=profile.language,
        total_sessions=session_count,
        total_duration_minutes=total_duration,
        sessions=sessions,
        prerequisite_edges=[],
        grounding_status=grounding_status,
        confidence=_confidence(grounding_status, profile),
        open_questions=_open_questions(grounding_status),
        low_confidence_decisions=_low_confidence_decisions(grounding_status, profile),
        rationale="retrieve grounding → Curricular-CoT adapt → validate; deterministic seam for unit planning.",
    )


def _session_count(profile: ClassProfile) -> int:
    if profile.prior_knowledge_gaps:
        return 4
    return 3


def _session_duration(profile: ClassProfile) -> int:
    match profile.attention_span_band:
        case "short":
            return 30
        case "medium":
            return 45
        case "long":
            return 60
        case unreachable:
            assert_never(unreachable)


def _bloom_levels(session_count: int, profile: ClassProfile) -> list[BloomLevel]:
    if profile.proficiency_level == "advanced":
        seed: list[BloomLevel] = ["understand", "apply", "analyze", "evaluate"]
    else:
        seed = ["remember", "understand", "apply", "analyze"]
    return seed[:session_count]


def _session(
    topic: str,
    order_index: int,
    duration: int,
    bloom: BloomLevel,
    profile: ClassProfile,
) -> SessionPlan:
    session_id = f"S{order_index:02d}"
    return SessionPlan(
        session_id=session_id,
        order_index=order_index,
        title=f"{topic}: session {order_index}",
        sub_topic=_sub_topic(topic, order_index, profile),
        duration_minutes=duration,
        learning_objectives=[f"Students can {bloom} {topic}"],
        bloom_level_primary=bloom,
        knowledge_components=[
            KnowledgeComponent(
                kc_id=f"KC-{session_id}-{index}",
                title=f"{topic} KC {index}",
                description=f"Core knowledge component {index} for {topic}",
            )
            for index in range(1, 3)
        ],
        recalled_kc_ids=[],
        prerequisite_sessions=[f"S{order_index - 1:02d}"] if order_index > 1 else [],
        methodology_primary=_methodology_for(bloom, profile),
    )


def _sub_topic(topic: str, order_index: int, profile: ClassProfile) -> str:
    if order_index == 1 and profile.prior_knowledge_gaps:
        return f"Reteach prerequisites for {topic}"
    return f"{topic} part {order_index}"


def _methodology_for(bloom: BloomLevel, profile: ClassProfile) -> MethodologyTag:
    if "quiet" in {need.casefold() for need in profile.differentiation_needs}:
        return "shy_student_1on1"
    match bloom:
        case "remember":
            return "active_recall"
        case "understand":
            return "concept_map"
        case "apply":
            return "timed_quiz"
        case "analyze":
            return "contrastive_pairs"
        case "evaluate" | "create":
            return "inverse_thinking"
        case unreachable:
            assert_never(unreachable)


def _confidence(grounding_status: GroundingStatus, profile: ClassProfile) -> float:
    match grounding_status:
        case "grounded":
            base = 0.86
        case "partial":
            base = 0.68
        case "ungrounded":
            base = 0.42
        case unreachable:
            assert_never(unreachable)
    return max(0.0, base - (0.08 if profile.prior_knowledge_gaps else 0.0))


def _open_questions(grounding_status: GroundingStatus) -> list[str]:
    return ["confirm curriculum pacing"] if grounding_status != "grounded" else []


def _low_confidence_decisions(
    grounding_status: GroundingStatus,
    profile: ClassProfile,
) -> list[str]:
    decisions: list[str] = []
    if grounding_status != "grounded":
        decisions.append("session count inferred without full curriculum grounding")
    if profile.prior_knowledge_gaps:
        decisions.append("first session biased toward reteaching due to persona gaps")
    return decisions


def _repair_sequence(sequence: LessonSequence) -> LessonSequence:
    issues = SequenceConsistencyValidator().validate(sequence)
    hard_issues = [issue for issue in issues if issue.severity is ConsistencySeverity.HARD]
    if not hard_issues:
        return sequence
    repaired_sessions = [
        session.model_copy(update={"knowledge_components": session.knowledge_components[:4]})
        for session in sequence.sessions
    ]
    repaired = sequence.model_copy(update={"sessions": repaired_sessions})
    remaining = [
        issue.rule
        for issue in SequenceConsistencyValidator().validate(repaired)
        if issue.severity is ConsistencySeverity.HARD
    ]
    if not remaining:
        return repaired
    return repaired.model_copy(update={
        "low_confidence_decisions": [
            *repaired.low_confidence_decisions,
            *(f"unresolved validator issue: {rule}" for rule in remaining),
        ],
    })


def _apply_soft_priors(sequence: LessonSequence, state: UnitPlannerNodeState) -> LessonSequence:
    preferences = state.get("teacher_preferences")
    if not isinstance(preferences, dict):
        return sequence
    preferred_duration = preferences.get("preferred_session_duration_minutes")
    if not isinstance(preferred_duration, int):
        return sequence
    bounded_duration = max(10, min(90, preferred_duration))
    sessions = [session.model_copy(update={"duration_minutes": bounded_duration}) for session in sequence.sessions]
    return sequence.model_copy(update={
        "sessions": sessions,
        "total_duration_minutes": bounded_duration * len(sessions),
        "low_confidence_decisions": [
            *sequence.low_confidence_decisions,
            "teacher decomposition-memory duration prior applied softly",
        ],
    })
