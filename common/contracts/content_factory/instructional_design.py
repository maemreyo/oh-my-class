"""Deterministic instructional design plans for Lesson/Presentation specialists."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

JsonObject = dict[str, Any]


class LessonPhasePlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    phase_id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    objective_ids: tuple[str, ...] = Field(min_length=1)
    timebox_minutes: int = Field(ge=1, le=180)
    teacher_actions: tuple[str, ...] = Field(min_length=1)
    student_actions: tuple[str, ...] = Field(min_length=1)
    materials: tuple[str, ...] = ()
    checks_for_understanding: tuple[str, ...] = Field(min_length=1)
    anticipated_responses: tuple[str, ...] = Field(min_length=1)
    misconception_responses: tuple[str, ...] = Field(min_length=1)
    differentiation: tuple[str, ...] = Field(min_length=1)
    transition: str = Field(min_length=1, max_length=500)
    closure: str = Field(min_length=1, max_length=500)


class InstructionalDesignPlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    plan_version: str = "instructional_design.v1"
    objective_ids: tuple[str, ...] = Field(min_length=1)
    phases: tuple[LessonPhasePlan, ...] = Field(min_length=1)
    allocated_minutes: int = Field(ge=1)
    transition_reserve_minutes: int = Field(ge=0)
    contingency_minutes: int = Field(ge=0)


def build_instructional_design_plan(lesson_plan: JsonObject) -> InstructionalDesignPlan:
    objectives = _objectives(lesson_plan)
    if not objectives:
        raise ValueError("instructional design requires approved objectives")
    phase_inputs = _phase_inputs(lesson_plan)
    if not phase_inputs:
        phase_inputs = [
            ("launch", "Activate prior knowledge and surface an initial prediction."),
            ("model", "Model the target thinking with a worked example."),
            ("guided_practice", "Guide learners through a similar task and check understanding."),
            ("independent_practice", "Learners apply the target skill independently."),
            ("closure", "Learners explain what changed in their understanding."),
        ]
    duration = _duration(lesson_plan)
    reserve = max(2, round(duration * 0.08))
    contingency = max(2, round(duration * 0.07))
    available = max(len(phase_inputs), duration - reserve - contingency)
    timeboxes = _distribute(available, len(phase_inputs))
    materials = tuple(_strings(lesson_plan.get("materials")))
    phases: list[LessonPhasePlan] = []
    for index, ((heading, detail), minutes) in enumerate(zip(phase_inputs, timeboxes, strict=True), start=1):
        objective_id = objectives[(index - 1) % len(objectives)][0]
        title = heading.replace("_", " ").strip().title()
        phases.append(LessonPhasePlan(
            phase_id=f"phase-{index}",
            title=title,
            objective_ids=(objective_id,),
            timebox_minutes=minutes,
            teacher_actions=(detail,),
            student_actions=(f"Perform the learner action for {title.casefold()} and make thinking visible.",),
            materials=materials,
            checks_for_understanding=(f"Collect one observable response linked to {objective_id}.",),
            anticipated_responses=("Correct response", "Partially correct response", "Common misconception"),
            misconception_responses=("Name the misconception, contrast it with evidence, then retry a near-transfer example.",),
            differentiation=("Reduce linguistic load without reducing the target knowledge.", "Offer an extension that preserves the objective."),
            transition=f"Connect the evidence from {title.casefold()} to the next phase.",
            closure=f"Record whether {objective_id} was demonstrated and what needs repair.",
        ))
    return InstructionalDesignPlan(
        objective_ids=tuple(objective_id for objective_id, _description in objectives),
        phases=tuple(phases),
        allocated_minutes=sum(timeboxes),
        transition_reserve_minutes=reserve,
        contingency_minutes=contingency,
    )


def _objectives(lesson_plan: JsonObject) -> list[tuple[str, str]]:
    raw = lesson_plan.get("learning_objectives")
    if not isinstance(raw, list):
        return []
    records: list[tuple[str, str]] = []
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
    return records


def _phase_inputs(lesson_plan: JsonObject) -> list[tuple[str, str]]:
    raw = lesson_plan.get("learning_plan")
    if not isinstance(raw, dict):
        return []
    phases: list[tuple[str, str]] = []
    for heading, value in raw.items():
        if isinstance(value, str) and value.strip():
            phases.append((str(heading), value.strip()))
        elif isinstance(value, dict):
            for key in ("content", "description", "activity"):
                detail = value.get(key)
                if isinstance(detail, str) and detail.strip():
                    phases.append((str(heading), detail.strip()))
                    break
    return phases


def _duration(lesson_plan: JsonObject) -> int:
    value = lesson_plan.get("duration_minutes")
    return value if isinstance(value, int) and 10 <= value <= 180 else 45


def _distribute(total: int, slots: int) -> list[int]:
    quotient, remainder = divmod(total, slots)
    return [quotient + (1 if index < remainder else 0) for index in range(slots)]


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]
