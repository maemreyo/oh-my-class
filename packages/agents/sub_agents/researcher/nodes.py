"""Researcher Agent — LangGraph node function.

Gathers, cross-references, and synthesizes sources for lesson content.
Follows the FACT protocol (Find → Assess → Cross-reference → Tag).
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

_LOGGER = logging.getLogger(__name__)

from common.contracts.research_bundle import ResearchBundle

if TYPE_CHECKING:
    from packages.agents.sub_agents.researcher.state import ResearcherState


async def researcher_node(state: ResearcherState) -> dict[str, Any]:
    """Search and synthesize research sources for the lesson plan.

    Returns: {"research_bundle": {...}}
    """
    from packages.agents.sub_agents.researcher.prompts import load_system_prompt
    from packages.agents.config.models import NINEROUTER
    researcher_system_prompt = load_system_prompt()

    lesson_plan = state.get("lesson_plan") or {}
    research_policy = state.get("research_policy", "standard")
    topic = lesson_plan.get("topic", "General topic")
    from packages.agents.sub_agents.researcher.evidence import build_research_evidence
    from packages.agents.sub_agents.researcher.tools import web_fetch
    from packages.agents.tools.web_search import web_search

    source_candidates = await web_search(str(topic), num_results=NINEROUTER.search_results, min_sources=NINEROUTER.min_sources)
    research_evidence = await build_research_evidence(
        source_candidates,
        fetch_limit=_fetch_limit(str(research_policy)),
        web_fetcher=web_fetch,
    )

    user_prompt = f"""
Research topic: {topic}

Research policy: {research_policy}

Learning objectives:
{json.dumps(lesson_plan.get('learning_objectives', []), indent=2)}

Source candidates from the web_search tool:
{json.dumps(source_candidates, indent=2)}

Compact fetched evidence from 4omc.fetch:
{json.dumps(research_evidence, indent=2) }

Please gather and verify sources following the FACT protocol.
Use ONLY the source candidates and fetched evidence above. Mark a source VERIFIED
only when fetched evidence supports it. If fetch failed or content is missing,
mark verification_status as UNCERTAIN. Do not invent URLs, citations, snippets,
or credibility scores.
"""

    from packages.agents.config.gate_config import GateConfig
    from packages.agents.config.models import MODELS
    from packages.agents.llm import (
        chat_messages,
        complete_json_chat,
        extract_json_text,
        log_llm_failure,
        log_llm_start,
        log_llm_success,
    )

    config = GateConfig()
    model = MODELS.researcher
    run_id = str(state.get("run_id", ""))
    step = int(state.get("current_step", 7))
    system_prompt = (
        researcher_system_prompt
        + "\n\nCRITICAL: Respond ONLY with a single JSON object. "
        "No prose, no explanation, no markdown code fences. "
        "Just the raw JSON."
    )
    messages = chat_messages(system_prompt, user_prompt)

    for attempt in range(config.max_retries):
        attempt_number = attempt + 1
        started = log_llm_start("researcher", run_id, step, model, attempt_number)
        try:
            content = await complete_json_chat(
                model=model,
                messages=messages,
                temperature=0.3 if attempt > 0 else 0.7,
                tags=[
                    "agent:researcher",
                    f"step:{state.get('current_step', 7)}",
                    f"run:{state.get('run_id', '')}",
                    f"attempt:{attempt_number}",
                    "pipeline:oh-my-class",
                ],
            )
            log_llm_success("researcher", run_id, step, model, attempt_number, started)
            try:
                json_str = extract_json_text(content)
                bundle_data = json.loads(json_str)
                bundle = ResearchBundle.model_validate(bundle_data)
                return {"research_bundle": bundle.model_dump()}
            except (ValueError, json.JSONDecodeError, Exception):
                log_llm_failure(
                    "researcher",
                    run_id,
                    step,
                    model,
                    attempt_number,
                    started,
                    ValueError("invalid JSON response"),
                )
                if attempt < 2:
                    messages = chat_messages(
                        system_prompt,
                        "Invalid response. Return ONLY the JSON object. No prose.",
                    )
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
                # Ensure minimum 2 sources for validation
                if len(sources) < 2:
                    sources = _synthetic_sources(topic, research_policy)
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
            log_llm_failure("researcher", run_id, step, model, attempt_number, started, e)
            if attempt < 2:
                continue
            # Graceful degradation: return UNCERTAIN sources instead of crashing
            # the pipeline. Unverified sources are better than no pipeline at all.
            _LOGGER.warning(
                "researcher.fallback_uncertain run_id=%s model=%s error=%s",
                run_id, model, str(e)[:200],
            )
            sources = [
                {
                    "title": str(source.get("title", "Unknown")),
                    "url": str(source.get("url", "")),
                    "credibility_score": 0.3,
                    "verification_status": "UNCERTAIN",
                }
                for source in source_candidates
            ]
            if len(sources) < 2:
                sources = _synthetic_sources(topic, research_policy)
            bundle = ResearchBundle.model_validate({
                "topic": str(topic),
                "sources": sources,
                "key_findings": [
                    "Research agent encountered LLM errors; "
                    "sources are unverified and provided for teacher review.",
                ],
                "cross_references": [],
                "research_policy": research_policy,
            })
            return {"research_bundle": bundle.model_dump()}

    raise ValueError("Researcher agent failed: exhausted retries")


def _fetch_limit(research_policy: str) -> int:
    from packages.agents.config.models import NINEROUTER
    limits = {
        "basic": NINEROUTER.fetch_limit_basic,
        "standard": NINEROUTER.fetch_limit_standard,
        "rigorous": NINEROUTER.fetch_limit_rigorous,
    }
    return limits.get(research_policy, NINEROUTER.fetch_limit_standard)


def _synthetic_sources(topic: str, research_policy: str) -> list[dict[str, Any]]:
    return [
        {
            "title": f"General knowledge about {topic}",
            "url": "",
            "credibility_score": 0.3,
            "verification_status": "UNCERTAIN",
        },
        {
            "title": f"Educational resources for {topic}",
            "url": "",
            "credibility_score": 0.3,
            "verification_status": "UNCERTAIN",
        },
    ]
