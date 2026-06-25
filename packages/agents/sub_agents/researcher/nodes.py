"""Researcher Agent — LangGraph node function.

Gathers, cross-references, and synthesizes sources for lesson content.
Follows the FACT protocol (Find → Assess → Cross-reference → Tag).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from common.contracts.research_bundle import ResearchBundle

if TYPE_CHECKING:
    from packages.agents.sub_agents.researcher.state import ResearcherState


async def researcher_node(state: ResearcherState) -> dict[str, Any]:
    """Search and synthesize research sources for the lesson plan.

    Returns: {"research_bundle": {...}}
    """
    import litellm

    from packages.agents.sub_agents.researcher.prompts import load_system_prompt
    researcher_system_prompt = load_system_prompt()

    lesson_plan = state.get("lesson_plan") or {}
    research_policy = state.get("research_policy", "standard")
    topic = lesson_plan.get("topic", "General topic")

    user_prompt = f"""
Research topic: {topic}

Research policy: {research_policy}

Learning objectives:
{json.dumps(lesson_plan.get('learning_objectives', []), indent=2)}

Please gather and verify sources following the FACT protocol.
"""

    messages = [
        {"role": "system", "content": researcher_system_prompt},
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
                        "agent:researcher",
                        f"step:{state.get('current_step', 7)}",
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

        bundle_data = json.loads(json_str)
        bundle = ResearchBundle.model_validate(bundle_data)
        return {"research_bundle": bundle.model_dump()}

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from LLM: {e}") from e
    except Exception as e:
        raise ValueError(f"Researcher agent failed: {e}") from e
