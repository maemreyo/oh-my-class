from __future__ import annotations

from common.contracts.component_strategy import ComponentStrategyRequest, StrategyQualityScore
from common.contracts.component_strategy_knowledge_models import ComponentBindingEntry


def family_id_for(request: ComponentStrategyRequest) -> str:
    subject = request.subject.lower()
    intents = set(request.assessment_intent)
    if "quiz" in request.artifact_types and ("exam_prep" in intents or "summative" in intents):
        return "exam_assessment_prep"
    if subject in {"language", "english", "vietnamese", "literature"}:
        return "vocabulary_language"
    return "concept_math_science"


def grade_band_for(grade_level: str) -> str:
    digits = "".join(char for char in grade_level if char.isdigit())
    grade = int(digits or "5")
    if grade <= 6:
        return "grade_4_6"
    if grade <= 9:
        return "grade_7_9"
    return "grade_10_12"


def subject_tag_for(request: ComponentStrategyRequest) -> str:
    if "quiz" in request.artifact_types and ("exam_prep" in request.assessment_intent or "summative" in request.assessment_intent):
        return "exam_prep"
    subject = request.subject.lower()
    if subject in {"language", "english", "vietnamese", "literature"}:
        return "language"
    return subject if subject in {"math", "science"} else "concept"


def phase_for(binding: ComponentBindingEntry) -> str:
    if "elicit_performance" in binding.gagne_events:
        return "practice"
    if "provide_guidance" in binding.gagne_events:
        return "guide"
    return "present"


def score_binding(binding: ComponentBindingEntry, request: ComponentStrategyRequest) -> float:
    score = 1.0
    if request.research_signals is not None:
        score += 0.1 * len(set(binding.evidence_ids).intersection(request.research_signals.evidence_tags))
    if request.teacher_preferences is not None:
        preferred = preference_values(request, "prefer_learning_move")
        if binding.learning_move_id in preferred:
            score *= 1.1
    return score


def quality_for(
    bindings: tuple[ComponentBindingEntry, ...],
    request: ComponentStrategyRequest,
) -> StrategyQualityScore:
    diversity = len({binding.component_type for binding in bindings}) / len(bindings)
    evidence = evidence_score(bindings, request)
    audit = {
        "bloom_moet_fit": 1.0,
        "gagne_fit": 1.0,
        "objective_alignment": 1.0,
        "evidence_coverage": evidence,
        "retrieval_formative_presence": retrieval_presence(bindings),
        "udl_coverage": len({tag for binding in bindings for tag in binding.udl_tags}) / 3,
        "duration_fit": 1.0,
        "diversity": diversity,
        "teacher_memory_multiplier": 1.0,
        "penalties": 0.0,
    }
    overall = min(1.0, (audit["objective_alignment"] + evidence + diversity) / 3)
    return StrategyQualityScore(
        overall=overall,
        objective_alignment=1.0,
        evidence_signal_coverage=evidence,
        component_diversity=diversity,
        compliance_safety="pass",
        audit_ledger=audit,
    )


def preference_values(request: ComponentStrategyRequest, event_type: str) -> set[str]:
    if request.teacher_preferences is None:
        return set()
    return {
        event.value
        for event in request.teacher_preferences.feedback_events
        if event.event_type == event_type
    }


def evidence_score(
    bindings: tuple[ComponentBindingEntry, ...],
    request: ComponentStrategyRequest,
) -> float:
    if request.research_signals is None or not request.research_signals.evidence_tags:
        return 0.5
    binding_evidence = {evidence for binding in bindings for evidence in binding.evidence_ids}
    matched = binding_evidence.intersection(request.research_signals.evidence_tags)
    return len(matched) / len(binding_evidence)


def retrieval_presence(bindings: tuple[ComponentBindingEntry, ...]) -> float:
    evidence = {evidence for binding in bindings for evidence in binding.evidence_ids}
    return 1.0 if "retrieval_practice" in evidence else 0.0
