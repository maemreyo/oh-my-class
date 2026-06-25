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

    from packages.agents.llm import get_llm_config, resolve_model

    llm_config = get_llm_config()
    try:
        response = await litellm.acompletion(
            model=resolve_model("f.light"),
            messages=messages,
            temperature=0.7,
            api_base=llm_config["api_base"],
            api_key=llm_config["api_key"],
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

        msg = response.choices[0].message
        reasoning = getattr(msg, "reasoning_content", None)
        content = msg.content

        from packages.agents.llm import extract_json_text

        json_str = extract_json_text(content, reasoning)
        plan_data = json.loads(json_str)
        plan = LessonPlan.model_validate(plan_data)
        return {"lesson_plan": plan.model_dump()}

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from LLM: {e}") from e
    except Exception as e:
        raise ValueError(f"Planner agent failed: {e}") from e
