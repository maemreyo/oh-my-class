from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class NoApprovedLessonDesignError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class LessonDesignScorecard:
    objective_coverage: float
    instructional_sequence: float
    pacing: float
    cognitive_load: float
    methodology_fidelity: float


def _objectives(lesson_plan: dict[str, Any]) -> list[str]:
    raw_objectives = lesson_plan.get("learning_objectives")
    if not isinstance(raw_objectives, list):
        return []
    objectives: list[str] = []
    for objective in raw_objectives:
        if isinstance(objective, str) and (text := objective.strip()):
            objectives.append(text)
        elif isinstance(objective, dict) and isinstance(objective.get("description"), str):
            if text := objective["description"].strip():
                objectives.append(text)
    return objectives


def _learning_phases(lesson_plan: dict[str, Any]) -> list[tuple[str, str]]:
    learning_plan = lesson_plan.get("learning_plan")
    if not isinstance(learning_plan, dict):
        return []
    phases: list[tuple[str, str]] = []
    for heading, detail in learning_plan.items():
        if isinstance(detail, str) and (content := detail.strip()):
            phases.append((str(heading), content))
        elif isinstance(detail, dict):
            content = detail.get("content", detail.get("description", detail.get("activity", "")))
            if isinstance(content, str) and content.strip():
                phases.append((str(heading), content.strip()))
    return phases


def _research_traces(research_brief: dict[str, Any]) -> list[dict[str, str]]:
    sources = research_brief.get("sources")
    if not isinstance(sources, list):
        return []
    traces: list[dict[str, str]] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        excerpt = source.get("excerpt")
        if not isinstance(excerpt, str) or not excerpt.strip():
            continue
        traces.append({
            "source_ref": str(source.get("title") or source.get("url") or "source"),
            "excerpt": excerpt.strip(),
        })
    return traces


def build_lesson_sections(lesson_plan: dict[str, Any]) -> list[dict[str, Any]]:
    objectives = _objectives(lesson_plan)
    phases = _learning_phases(lesson_plan)
    sections: list[dict[str, Any]] = [
        {"id": f"objective-{index}", "type": "objective", "title": "Learning objective", "content": objective}
        for index, objective in enumerate(objectives, start=1)
    ]
    sections.extend(
        {
            "id": f"phase-{index}",
            "title": heading.replace("_", " ").strip().title(),
            "content": content,
        }
        for index, (heading, content) in enumerate(phases, start=1)
    )
    return sections


def score_lesson_design(lesson_plan: dict[str, Any], sections: list[dict[str, Any]]) -> LessonDesignScorecard:
    objectives = _objectives(lesson_plan)
    phases = _learning_phases(lesson_plan)
    objective_sections = [section for section in sections if section.get("type") == "objective"]
    phase_sections = [section for section in sections if str(section.get("id", "")).startswith("phase-")]
    objective_coverage = round(len(objective_sections) / len(objectives), 3) if objectives else 0.0
    instructional_sequence = round(len(phase_sections) / len(phases), 3) if phases else 0.0
    duration = lesson_plan.get("duration_minutes")
    pacing = 1.0 if isinstance(duration, int) and 10 <= duration <= 180 else 0.0
    cognitive_load = 1.0 if len(objectives) <= 4 else round(4 / len(objectives), 3)
    methodology = lesson_plan.get("methodology") or lesson_plan.get("methodology_primary")
    methodology_fidelity = 1.0 if isinstance(methodology, (str, dict)) and methodology else 0.0
    return LessonDesignScorecard(
        objective_coverage=objective_coverage,
        instructional_sequence=instructional_sequence,
        pacing=pacing,
        cognitive_load=cognitive_load,
        methodology_fidelity=methodology_fidelity,
    )


def generate_lesson_design_artifact(
    lesson_plan: dict[str, Any],
    research_brief: dict[str, Any],
    *,
    theme: str = "default",
) -> dict[str, Any]:
    if not _objectives(lesson_plan):
        raise NoApprovedLessonDesignError("no approved learning objectives to design a lesson around")
    sections = build_lesson_sections(lesson_plan)
    scorecard = score_lesson_design(lesson_plan, sections)
    topic = str(lesson_plan.get("topic") or lesson_plan.get("title") or "the lesson").strip()
    return {
        "artifact_type": "lesson",
        "theme": theme,
        "title": f"Lesson: {topic}",
        "sections": sections,
        "metadata": {
            "summary": str(lesson_plan.get("summary") or "").strip(),
            "lesson_design_scorecard": {
                "objective_coverage": scorecard.objective_coverage,
                "instructional_sequence": scorecard.instructional_sequence,
                "pacing": scorecard.pacing,
                "cognitive_load": scorecard.cognitive_load,
                "methodology_fidelity": scorecard.methodology_fidelity,
            },
            "research_traces": _research_traces(research_brief),
        },
        "accessibility": {"language": str(lesson_plan.get("locale") or "vi")},
    }
