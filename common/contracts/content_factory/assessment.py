"""Assessment item blueprints, verification policy, and practice progression."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

JsonObject = dict[str, Any]
VerificationMethod = Literal["solver", "declared_answer", "rubric", "teacher_review"]
PracticeStage = Literal["worked_example", "guided", "independent", "retrieval", "interleaved", "transfer"]


class AssessmentItemBlueprint(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    item_id: str = Field(min_length=1, max_length=120)
    objective_id: str = Field(min_length=1, max_length=120)
    knowledge_component_id: str = Field(min_length=1, max_length=120)
    cognitive_demand: str = Field(min_length=1, max_length=80)
    difficulty: Literal["foundational", "developing", "secure", "transfer"]
    misconception_target_id: str = Field(min_length=1, max_length=160)
    evidence_statement_id: str = Field(min_length=1, max_length=160)
    response_type: str = Field(min_length=1, max_length=80)
    scoring_method: str = Field(min_length=1, max_length=80)
    verification_method: VerificationMethod
    practice_stage: PracticeStage | None = None


class AssessmentVerificationError(ValueError):
    pass


def build_item_blueprints(
    lesson_plan: JsonObject,
    *,
    count: int,
    response_type: str,
    practice: bool,
) -> tuple[AssessmentItemBlueprint, ...]:
    objectives = _objectives(lesson_plan)
    if not objectives:
        raise ValueError("assessment blueprints require approved objectives")
    subject = str(lesson_plan.get("subject") or "general").strip().casefold().replace(" ", "_")
    method: VerificationMethod
    if response_type in {"essay", "constructed_response", "short_answer"}:
        method = "rubric"
    elif subject in {"math", "science"}:
        method = "solver"
    elif subject in {"language_and_literacy", "humanities_and_social_studies"}:
        method = "declared_answer"
    else:
        method = "teacher_review"
    stages = _practice_stages(count) if practice else [None] * count
    blueprints: list[AssessmentItemBlueprint] = []
    for index in range(count):
        objective_id, _description, bloom = objectives[index % len(objectives)]
        stage = stages[index]
        difficulty = _difficulty(index, count, stage)
        item_id = f"{response_type}-{objective_id}-{index + 1}"
        blueprints.append(AssessmentItemBlueprint(
            item_id=item_id,
            objective_id=objective_id,
            knowledge_component_id=f"kc:{objective_id}",
            cognitive_demand=bloom or _demand_for_difficulty(difficulty),
            difficulty=difficulty,
            misconception_target_id=f"misconception:{objective_id}:common",
            evidence_statement_id=f"evidence:{objective_id}:{index + 1}",
            response_type=response_type,
            scoring_method="deterministic" if method in {"solver", "declared_answer"} else "analytic_rubric",
            verification_method=method,
            practice_stage=stage,
        ))
    return tuple(blueprints)


def validate_question_card(question: JsonObject, blueprint: AssessmentItemBlueprint) -> None:
    options = question.get("options")
    answer = question.get("answer")
    if blueprint.response_type == "selected_response" and isinstance(options, dict):
        normalized = [str(value).strip().casefold() for value in options.values() if str(value).strip()]
        if len(normalized) != len(set(normalized)):
            raise AssessmentVerificationError(f"{blueprint.item_id}: duplicate option or distractor collision")
        if answer not in options:
            raise AssessmentVerificationError(f"{blueprint.item_id}: declared answer is not an option id")
        correct_value = str(options[answer]).strip().casefold()
        if sum(value == correct_value for value in normalized) != 1:
            raise AssessmentVerificationError(f"{blueprint.item_id}: multiple equivalent correct options")
    if blueprint.verification_method == "solver" and not question.get("verification"):
        raise AssessmentVerificationError(f"{blueprint.item_id}: solver-supported item has no solver trace")


def _objectives(lesson_plan: JsonObject) -> list[tuple[str, str, str | None]]:
    raw = lesson_plan.get("learning_objectives")
    if not isinstance(raw, list):
        return []
    records: list[tuple[str, str, str | None]] = []
    for index, item in enumerate(raw, start=1):
        if isinstance(item, str) and item.strip():
            records.append((f"objective-{index}", item.strip(), None))
        elif isinstance(item, dict):
            description = item.get("description")
            if not isinstance(description, str) or not description.strip():
                continue
            objective_id = item.get("objective_id")
            bloom = item.get("bloom_level")
            records.append((
                objective_id.strip() if isinstance(objective_id, str) and objective_id.strip() else f"objective-{index}",
                description.strip(),
                bloom.strip() if isinstance(bloom, str) and bloom.strip() else None,
            ))
    return records


def _practice_stages(count: int) -> list[PracticeStage]:
    canonical: list[PracticeStage] = [
        "worked_example", "guided", "independent", "retrieval", "interleaved", "transfer",
    ]
    if count <= len(canonical):
        return canonical[:count]
    return [canonical[min(index, len(canonical) - 1)] for index in range(count)]


def _difficulty(index: int, count: int, stage: PracticeStage | None) -> Literal["foundational", "developing", "secure", "transfer"]:
    if stage in {"worked_example", "guided"}:
        return "foundational" if stage == "worked_example" else "developing"
    if stage == "transfer" or index == count - 1:
        return "transfer"
    if stage in {"retrieval", "interleaved"}:
        return "secure"
    ratio = (index + 1) / max(count, 1)
    if ratio <= 0.25:
        return "foundational"
    if ratio <= 0.6:
        return "developing"
    return "secure"


def _demand_for_difficulty(difficulty: str) -> str:
    return {
        "foundational": "understand",
        "developing": "apply",
        "secure": "analyze",
        "transfer": "evaluate",
    }[difficulty]
