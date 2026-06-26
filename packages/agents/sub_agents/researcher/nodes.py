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

    from packages.agents.llm import extract_json_text, get_llm_config, resolve_model

    llm_config = get_llm_config()
    # Strong system prompt to force JSON output from free models
    messages[0]["content"] = (
        messages[0]["content"]
        + "\n\nCRITICAL: Respond ONLY with a single JSON object. "
        "No prose, no explanation, no markdown code fences. "
        "Just the raw JSON."
    )

    response = None
    for attempt in range(3):
        try:
            response = await litellm.acompletion(
                model=resolve_model("f.light"),
                messages=messages,
                temperature=0.3 if attempt > 0 else 0.7,
                api_base=llm_config["api_base"],
                api_key=llm_config["api_key"],
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
            msg = response.choices[0].message
            reasoning = getattr(msg, "reasoning_content", None)
            content = msg.content
            try:
                json_str = extract_json_text(content, reasoning)
                bundle_data = json.loads(json_str)
                bundle = ResearchBundle.model_validate(bundle_data)
                return {"research_bundle": bundle.model_dump()}
            except (ValueError, json.JSONDecodeError, Exception) as parse_err:
                if attempt < 2:
                    messages.append({"role": "assistant", "content": str(content)[:500]})
                    messages.append({
                        "role": "user",
                        "content": "Invalid response. Return ONLY the JSON object. No prose.",
                    })
                    continue
                raise
        except Exception as e:
            if attempt < 2:
                continue
            raise ValueError(f"Researcher agent failed: {e}") from e

    raise ValueError("Researcher agent failed: exhausted retries")
