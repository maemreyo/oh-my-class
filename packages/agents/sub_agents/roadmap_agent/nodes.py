"""Roadmap Agent — LangGraph node function.

Generates a personalised RoadmapContent artifact from DiagnosticReport + StudentProfile.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from common.contracts.roadmap import RoadmapContent
from packages.agents.sub_agents.roadmap_agent.tools import book_recommender, milestone_calculator

if TYPE_CHECKING:
    from packages.agents.sub_agents.roadmap_agent.state import RoadmapAgentState


async def roadmap_node(state: RoadmapAgentState) -> dict[str, Any]:
    """Generate a RoadmapContent JSON artifact for the student.

    Returns: {"roadmap_artifact": {...}, "artifacts": [{"type": "roadmap", ...}]}
    """
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

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    from packages.agents.llm import (
        complete_json_chat,
        log_llm_failure,
        log_llm_start,
        log_llm_success,
        resolve_model,
    )

    model = resolve_model("f.light")
    run_id = str(state.get("run_id", ""))
    step = int(state.get("current_step", 0))

    started = log_llm_start("roadmap_agent", run_id, step, model, 1)
    try:
        content = await complete_json_chat(
            model=model,
            messages=messages,
            temperature=0.5,
            tags=[
                "agent:roadmap_agent",
                f"step:{state.get('current_step', 0)}",
                f"run:{state.get('run_id', '')}",
                "pipeline:oh-my-class",
            ],
        )
        log_llm_success("roadmap_agent", run_id, step, model, 1, started)

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
        log_llm_failure("roadmap_agent", run_id, step, model, 1, started, e)
        raise ValueError(f"Invalid JSON from LLM: {e}") from e
    except Exception as e:
        log_llm_failure("roadmap_agent", run_id, step, model, 1, started, e)
        raise ValueError(f"Roadmap agent failed: {e}") from e
