"""Planner Agent — LangGraph node function.

Generates structured lesson plans using backward design (UbD) principles
and Gagné's 9-event instruction model. Output validated against LessonPlan schema.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from common.contracts.lesson_plan import LessonPlan

if TYPE_CHECKING:
    from packages.agents.sub_agents.planner.state import PlannerState


async def planner_node(state: PlannerState) -> dict[str, Any]:
    """Design a lesson blueprint from raw_request + class_info.

    Returns: {"lesson_plan": {...}}
    """
    from packages.agents.sub_agents.planner.prompts import load_system_prompt
    planner_system_prompt = load_system_prompt()

    user_prompt = f"""
Teacher request: {state['raw_request']}

Class information:
- Grade: {state['class_info'].get('grade', 'Unknown')}
- Subject: {state['class_info'].get('subject', 'Unknown')}
- Student count: {state['class_info'].get('student_count', 'Unknown')}
- Language: {state['class_info'].get('language', 'en')}
"""

    from packages.agents.llm import (
        chat_messages,
        complete_json_chat,
        extract_json_text,
        log_llm_failure,
        log_llm_start,
        log_llm_success,
        resolve_model,
    )

    model = resolve_model("f.light")
    run_id = str(state.get("run_id", ""))
    step = int(state.get("current_step", 3))
    system_prompt = (
        planner_system_prompt
        + "\n\nCRITICAL: Respond ONLY with a single JSON object. "
        "No prose, no explanation, no markdown code fences."
    )
    messages = chat_messages(system_prompt, user_prompt)

    for attempt in range(3):
        attempt_number = attempt + 1
        started = log_llm_start("planner", run_id, step, model, attempt_number)
        try:
            content = await complete_json_chat(
                model=model,
                messages=messages,
                temperature=0.3 if attempt > 0 else 0.7,
                tags=[
                    "agent:planner",
                    f"step:{state.get('current_step', 3)}",
                    f"run:{state.get('run_id', '')}",
                    "pipeline:oh-my-class",
                ],
            )
            log_llm_success("planner", run_id, step, model, attempt_number, started)
            json_str = extract_json_text(content)
            plan_data = json.loads(json_str)
            plan = LessonPlan.model_validate(plan_data)
            return {"lesson_plan": plan.model_dump()}
        except (ValueError, json.JSONDecodeError) as parse_err:
            log_llm_failure(
                "planner", run_id, step, model, attempt_number, started, parse_err,
            )
            if attempt < 2:
                messages = chat_messages(
                    system_prompt,
                    "Invalid response. Return ONLY the JSON object.",
                )
                continue
            raise ValueError(f"Planner agent failed: {parse_err}") from parse_err
        except Exception as e:
            log_llm_failure("planner", run_id, step, model, attempt_number, started, e)
            if attempt < 2:
                continue
            raise ValueError(f"Planner agent failed: {e}") from e

    raise ValueError("Planner agent failed: exhausted retries")
