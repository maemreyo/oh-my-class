"""Roadmap Agent — LangGraph node function.

Generates a personalised RoadmapContent artifact from DiagnosticReport + StudentProfile.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from common.contracts.roadmap import RoadmapContent
from packages.agents.sub_agents.roadmap_agent.tools import book_recommender, milestone_calculator
from packages.agents.teaching_pack.stages import StageEnum, stage_number

if TYPE_CHECKING:
    from packages.agents.sub_agents.roadmap_agent.state import RoadmapAgentState


async def roadmap_node(state: RoadmapAgentState) -> dict[str, Any]:
    """Generate a RoadmapContent JSON artifact for the student.

    Returns: {"roadmap_artifact": {...}, "artifacts": [{"type": "roadmap", ...}]}
    """
    if state.get("use_structured_roadmap", False):
        return _structured_roadmap(state)

    from packages.agents.sub_agents.roadmap_agent.prompts import load_system_prompt

    system_prompt = load_system_prompt()

    diagnostic_report = state.get("diagnostic_report") or {}
    student_profile = state.get("student_profile") or {}

    level = diagnostic_report.get("recommended_level", "B2")
    weaknesses = student_profile.get("weaknesses", [])
    target_score = student_profile.get("target_score") or 40
    error_rate = diagnostic_report.get("overall_error_rate", 0.5)
    months = student_profile.get("study_duration_months", 6)

    book_recs = book_recommender(level, weaknesses)
    milestones = milestone_calculator(target_score, error_rate, months)

    user_prompt = f"""Generate a personalised learning roadmap.

DiagnosticReport:
{json.dumps(diagnostic_report, ensure_ascii=False, indent=2)}

StudentProfile:
{json.dumps(student_profile, ensure_ascii=False, indent=2)}

Book Recommendations:
{json.dumps(book_recs, ensure_ascii=False, indent=2)}

Monthly Milestones:
{json.dumps(milestones, ensure_ascii=False, indent=2)}
"""

    from packages.agents.config.models import MODELS
    from packages.agents.runtime import AgentRuntime, AgentRuntimeConfig

    model = MODELS.blueprint_design
    run_id = str(state.get("run_id", ""))
    current_step = state.get("current_step", StageEnum.UNIT_PREP)
    step = stage_number(current_step)
    runtime = AgentRuntime(AgentRuntimeConfig(
        agent="roadmap_agent",
        run_id=run_id,
        step=step,
        step_label=current_step.value,
        model=model,
        base_temperature=0.5,
        retry_temperature=0.5,
    ))
    messages = runtime.messages(system_prompt, user_prompt)

    try:
        content = await runtime.complete_json(
            messages=messages,
            attempt=0,
        )

        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content.strip()

        roadmap_data = json.loads(json_str)
        roadmap_data.setdefault("artifact_type", "roadmap")
        validated = RoadmapContent.model_validate(roadmap_data)
        roadmap_data = validated.model_dump()

        artifact_entry = {
            "id": f"roadmap-{diagnostic_report.get('student_id', 'unknown')}",
            "type": "roadmap",
            "data": roadmap_data,
        }

        return {
            "roadmap_artifact": roadmap_data,
            "artifacts": [artifact_entry],
        }

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from LLM: {e}") from e
    except Exception as e:
        raise ValueError(f"Roadmap agent failed: {e}") from e


def _structured_roadmap(state: RoadmapAgentState) -> dict[str, Any]:
    diagnostic_report = state.get("diagnostic_report") or {}
    student_profile = state.get("student_profile") or {}
    focus_areas = _focus_areas(diagnostic_report)
    months = _months(student_profile)
    sections = [_milestone_section(index, focus_areas, student_profile, state.get("kt_mastery") or {}) for index in range(1, months + 1)]
    roadmap = RoadmapContent(
        title="Personalized macro roadmap",
        theme="default",
        hero={
            "eyebrow": "Macro plan",
            "title": f"{_exam(student_profile)} roadmap",
            "lede": "Milestones compose into unit-planning inputs; no lesson content is generated here.",
        },
        sections=sections,
        sidebar={
            "title": "Focus",
            "subtitle": ", ".join(focus_areas),
            "nav": [{"label": section.title, "href": f"#{section.id}"} for section in sections],
        },
    ).model_dump()
    roadmap["metadata"] = {
        "generation_mode": "milestone_to_unit_macro",
        "focus_areas": focus_areas,
        "personalization": _personalization(student_profile),
    }
    unit_inputs = [_unit_input(section, focus_areas, state) for section in sections]
    return {
        "roadmap_artifact": roadmap,
        "unit_decomposition_inputs": unit_inputs,
        "artifacts": [{"id": f"roadmap-{diagnostic_report.get('student_id', 'unknown')}", "type": "roadmap", "data": roadmap}],
    }


def _milestone_section(
    index: int,
    focus_areas: list[str],
    student_profile: dict[str, Any],
    kt_mastery: dict[str, Any],
):
    from common.contracts.roadmap import RoadmapSection

    focus = focus_areas[(index - 1) % len(focus_areas)] if focus_areas else "general skill"
    mastery = _mastery_for(focus, kt_mastery)
    title_prefix = "Reteach" if mastery < 0.5 else "Extend"
    personalization = _personalization(student_profile)
    return RoadmapSection(
        id=f"milestone-{index}",
        title=f"{title_prefix} {focus}",
        subtitle=f"{_exam(student_profile)} skill milestone {index}",
        tag_num=str(index),
        components=[
            {"type": "paragraph", "text": f"Focus area: {focus}. {personalization}"},
            {"type": "paragraph", "text": "Compose this milestone into a topic-decomposition unit."},
        ],
    )


def _unit_input(section, focus_areas: list[str], state: RoadmapAgentState) -> dict[str, Any]:
    return {
        "mode": "plan_unit",
        "parent_run_id": state.get("run_id", ""),
        "milestone_id": section.id,
        "topic": section.title,
        "focus_areas": focus_areas,
    }


def _focus_areas(diagnostic_report: dict[str, Any]) -> list[str]:
    gaps = diagnostic_report.get("knowledge_gaps")
    if not isinstance(gaps, list):
        return ["general skill"]
    areas = [str(gap.get("category")) for gap in gaps if isinstance(gap, dict) and gap.get("category")]
    return areas or ["general skill"]


def _personalization(student_profile: dict[str, Any]) -> str:
    traits = student_profile.get("personality_traits")
    trait_names: set[str] = set()
    if isinstance(traits, list):
        trait_names = {str(trait.get("trait")) for trait in traits if isinstance(trait, dict)}
    if "shy" in trait_names:
        return "Use low-pressure individual practice and avoid group performance."
    if "film_learner" in trait_names:
        return "Use short video anchors before practice."
    if "depth_oriented" in trait_names:
        return "Include explain why reasoning before drills."
    return "Use balanced independent practice."


def _exam(student_profile: dict[str, Any]) -> str:
    value = student_profile.get("target_exam")
    return str(value) if value else "Skill-based"


def _months(student_profile: dict[str, Any]) -> int:
    value = student_profile.get("study_duration_months")
    if isinstance(value, int):
        return max(1, min(12, value))
    return 3


def _mastery_for(focus: str, kt_mastery: dict[str, Any]) -> float:
    value = kt_mastery.get(focus)
    if isinstance(value, dict):
        mastery = value.get("mastery")
        if isinstance(mastery, int | float):
            return float(mastery)
    return 0.0
