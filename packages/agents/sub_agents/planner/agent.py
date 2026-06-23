"""Planner Agent — node implementation.

Generates structured lesson plans using backward design (UbD) principles
and Gagné's 9-event instruction model. Output validated against
LessonPlan Pydantic schema.

Uses deepseek-v4-flash via 9Router combo: f.light (fast free tier)
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from common.contracts.lesson_plan import LessonPlan

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


async def design_lesson_plan(state: OhMyClassState) -> dict[str, Any]:
    """LangGraph node for the Planner Agent.

    Takes the teacher's raw request and class info, produces a structured
    LessonPlan JSON conforming to common.contracts.lesson_plan.LessonPlan.

    Args:
        state: Current pipeline state with raw_request and class_info.

    Returns:
        Partial state update containing 'lesson_plan' dict.

    Output contract:
        LessonPlan with topic, grade_level, subject, duration_minutes,
        learning_objectives (≥2 Bloom levels), prerequisite_knowledge,
        learning_plan (Gagné 9-event), assessment_checkpoints.
    """
    import litellm

    from packages.agents.sub_agents.planner.prompts import PLANNER_SYSTEM_PROMPT

    user_prompt = f"""
Teacher request: {state['raw_request']}

Class information:
- Grade: {state['class_info'].get('grade', 'Unknown')}
- Subject: {state['class_info'].get('subject', 'Unknown')}
- Student count: {state['class_info'].get('student_count', 'Unknown')}
- Language: {state['class_info'].get('language', 'en')}
"""

    messages = [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = await litellm.acompletion(
            model="deepseek-v4-flash",
            messages=messages,
            temperature=0.7,
            extra_body={
                "metadata": {
                    "tags": [
                        "agent:planner",
                        f"step:{state.get('current_step', 3)}",
                        f"run:{state['run_id']}",
                        "pipeline:oh-my-class",
                    ]
                }
            },
        )

        content = response.choices[0].message.content

        # Strip markdown code fences if present
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
