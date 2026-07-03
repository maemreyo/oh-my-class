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
from packages.agents.sub_agents.researcher.runtime_grounding import (
    attach_excerpts,
    excerpts_by_url,
    finalize_bundle,
    remember_verified_sources,
    target_terms,
)
from packages.agents.teaching_pack.stages import StageEnum, stage_number

if TYPE_CHECKING:
    from packages.agents.sub_agents.researcher.state import ResearcherNodeState


async def researcher_node(state: ResearcherNodeState) -> dict[str, Any]:
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
    from packages.agents.sub_agents.researcher.grounding import (
        RESEARCH_MEMORY_CACHE,
        cache_key,
        policy_rigor,
        utc_now,
    )
    from packages.agents.sub_agents.researcher.tools import web_fetch
    from packages.agents.tools.web_search import web_search

    rigor = policy_rigor(str(research_policy), str(lesson_plan.get("subject", "")))
    memory_key = cache_key(topic, state.get("class_info", {}))
    cached_sources = RESEARCH_MEMORY_CACHE.get(memory_key, now=utc_now(), recency_days=rigor.recency_days)
    if cached_sources is not None:
        bundle = ResearchBundle.model_validate({
            "topic": str(topic),
            "sources": list(cached_sources),
            "key_findings": ["Reused verified grounding corpus from research memory cache."],
            "cross_references": [],
            "research_policy": research_policy,
        })
        return {"research_bundle": bundle.model_dump()}

    source_candidates = await web_search(str(topic), num_results=NINEROUTER.search_results, min_sources=NINEROUTER.min_sources)
    research_evidence = await build_research_evidence(
        source_candidates,
        fetch_limit=rigor.sources_per_claim_cap,
        web_fetcher=web_fetch,
    )
    # Deterministic (not LLM-decided): the fetched bodies ARE the grounding corpus the
    # Layer-2 fact_check consumes. Persist them into the bundle sources by URL so the
    # verified corpus carries its evidence instead of dropping it into the prompt only.
    fetched_excerpts = excerpts_by_url(research_evidence)
    terms = target_terms(lesson_plan, topic)

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
    from packages.agents.llm import extract_json_text
    from packages.agents.runtime import AgentRuntime, AgentRuntimeConfig

    config = GateConfig()
    model = MODELS.researcher
    run_id = str(state.get("run_id", ""))
    current_step = state.get("current_step", StageEnum.POST_BLUEPRINT_RESEARCH)
    step = stage_number(current_step)
    system_prompt = (
        researcher_system_prompt
        + "\n\nCRITICAL: Respond ONLY with a single JSON object. "
        "No prose, no explanation, no markdown code fences. "
        "Just the raw JSON."
    )
    runtime = AgentRuntime(AgentRuntimeConfig(
        agent="researcher",
        run_id=run_id,
        step=step,
        step_label=current_step.value,
        model=model,
        max_retries=config.max_retries,
        base_temperature=0.7,
        retry_temperature=0.3,
    ))
    messages = runtime.messages(system_prompt, user_prompt)

    try:
        bundle = await runtime.complete_json_with_retries(
            messages=messages,
            parse=lambda content: ResearchBundle.model_validate(json.loads(extract_json_text(content))),
            retry_messages=lambda _error, _content: runtime.messages(
                system_prompt,
                "Invalid response. Return ONLY the JSON object. No prose.",
            ),
        )
        finalized = finalize_bundle(bundle.model_dump(), fetched_excerpts, terms)
        remember_verified_sources(memory_key, finalized)
        return {"research_bundle": finalized}
    except (ValueError, json.JSONDecodeError) as exc:
        finalized = _fallback_uncertain_bundle(
            topic,
            source_candidates,
            research_policy,
            fetched_excerpts,
            terms,
            verified=False,
        )
        remember_verified_sources(memory_key, finalized)
        return {"research_bundle": finalized}
    except Exception as exc:
        _LOGGER.warning(
            "researcher.fallback_uncertain run_id=%s model=%s error=%s",
            run_id, model, str(exc)[:200],
        )
        finalized = _fallback_uncertain_bundle(
            topic,
            source_candidates,
            research_policy,
            fetched_excerpts,
            terms,
            verified=False,
        )
        remember_verified_sources(memory_key, finalized)
        return {"research_bundle": finalized}


def _synthetic_sources(topic: str) -> list[dict[str, Any]]:
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


def _fallback_uncertain_bundle(
    topic: Any,
    source_candidates: list[dict[str, Any]],
    research_policy: Any,
    fetched_excerpts: dict[str, str],
    terms: set[str],
    *,
    verified: bool,
) -> dict[str, Any]:
    sources = [
        {
            "title": str(source.get("title", "Unknown")),
            "url": str(source.get("url", "")),
            "credibility_score": 0.5 if verified else 0.3,
            "verification_status": "UNCERTAIN",
        }
        for source in source_candidates
    ]
    if len(sources) < 2:
        sources = _synthetic_sources(str(topic))
    bundle = ResearchBundle.model_validate({
        "topic": str(topic),
        "sources": sources,
        "key_findings": [
            "Research could not be fully verified automatically; sources are provided for teacher review.",
        ],
        "cross_references": [],
        "research_policy": research_policy,
    })
    return finalize_bundle(bundle.model_dump(), fetched_excerpts, terms)
