"""Researcher Agent — node implementation.

Gathers, cross-references, and synthesizes sources for lesson content.
Follows the FACT protocol (Find → Assess → Cross-reference → Tag).
Minimum verification: 2 independent sources for every HIGH-risk claim.

Uses deepseek-v4-flash via 9Router combo: f.light (fast free tier)
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from common.contracts.research_bundle import ResearchBundle

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


async def research_sources(state: OhMyClassState) -> dict[str, Any]:
    """LangGraph node for the Researcher Agent.

    Takes the approved lesson plan and gathers research sources.
    Verifies factual claims against ≥2 independent sources.

    Args:
        state: Current pipeline state with lesson_plan and research_policy.

    Returns:
        Partial state update containing 'research_bundle' dict.

    Research policies:
        - basic: 2-3 sources, factual accuracy only
        - standard: 5+ sources, citations required
        - rigorous: 10+ sources, peer-reviewed preferred
    """
    import litellm

    from packages.agents.sub_agents.researcher.prompts import RESEARCHER_SYSTEM_PROMPT

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
        {"role": "system", "content": RESEARCHER_SYSTEM_PROMPT},
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
                        "agent:researcher",
                        f"step:{state.get('current_step', 7)}",
                        f"run:{state['run_id']}",
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
