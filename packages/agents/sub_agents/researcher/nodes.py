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
    from packages.agents.tools.web_search import web_search

    source_candidates = await web_search(str(topic), num_results=5, min_sources=2)

    user_prompt = f"""
Research topic: {topic}

Research policy: {research_policy}

Learning objectives:
{json.dumps(lesson_plan.get('learning_objectives', []), indent=2)}

Source candidates from the web_search tool:
{json.dumps(source_candidates, indent=2)}

Please gather and verify sources following the FACT protocol.
Use ONLY the source candidates above. If you did not fetch a page body, mark
verification_status as UNCERTAIN rather than VERIFIED. Do not invent URLs,
citations, snippets, or credibility scores.
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
            response: Any = await litellm.acompletion(
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
            except (ValueError, json.JSONDecodeError, Exception):
                if attempt < 2:
                    messages.append({"role": "assistant", "content": str(content)[:500]})
                    messages.append({
                        "role": "user",
                        "content": "Invalid response. Return ONLY the JSON object. No prose.",
                    })
                    continue
                sources = [
                    {
                        "title": str(source["title"]),
                        "url": str(source["url"]),
                        "credibility_score": 0.5,
                        "verification_status": "UNCERTAIN",
                    }
                    for source in source_candidates
                ]
                bundle = ResearchBundle.model_validate({
                    "topic": str(topic),
                    "sources": sources,
                    "key_findings": [
                        "Research could not be fully verified automatically; "
                        "sources are provided for teacher review.",
                    ],
                    "cross_references": [],
                    "research_policy": research_policy,
                })
                return {"research_bundle": bundle.model_dump()}
        except Exception as e:
            if attempt < 2:
                continue
            raise ValueError(f"Researcher agent failed: {e}") from e

    raise ValueError("Researcher agent failed: exhausted retries")
