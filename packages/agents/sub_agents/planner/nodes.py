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
    import litellm

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

    messages = [
        {"role": "system", "content": planner_system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = await litellm.acompletion(
            model="f.light",
            messages=messages,
            temperature=0.7,
            extra_body={
                "metadata": {
                    "tags": [
                        "agent:planner",
                        f"step:{state.get('current_step', 3)}",
                        f"run:{state.get('run_id', '')}",
                        "pipeline:oh-my-class",
                    ]
                }
            },
        )

        content = response.choices[0].message.content

        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content.strip()

        plan_data = json.loads(json_str)
        plan = LessonPlan.model_validate(plan_data)
        return {"lesson_plan": plan.model_dump()}

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from LLM: {e}") from e
    except Exception as e:
        raise ValueError(f"Planner agent failed: {e}") from e
