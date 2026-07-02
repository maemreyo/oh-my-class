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
    from packages.agents.sub_agents.researcher.tools import web_fetch
    from packages.agents.tools.web_search import web_search

    source_candidates = await web_search(str(topic), num_results=NINEROUTER.search_results, min_sources=NINEROUTER.min_sources)
    research_evidence = await build_research_evidence(
        source_candidates,
        fetch_limit=_fetch_limit(str(research_policy)),
        web_fetcher=web_fetch,
    )
    # Deterministic (not LLM-decided): the fetched bodies ARE the grounding corpus the
    # Layer-2 fact_check consumes. Persist them into the bundle sources by URL so the
    # verified corpus carries its evidence instead of dropping it into the prompt only.
    fetched_excerpts = _excerpts_by_url(research_evidence)
    target_terms = _target_terms(lesson_plan, topic)

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
                return {"research_bundle": _finalize_bundle(bundle.model_dump(), fetched_excerpts, target_terms)}
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
                return {"research_bundle": _finalize_bundle(bundle.model_dump(), fetched_excerpts, target_terms)}
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
            return {"research_bundle": _attach_excerpts(bundle.model_dump(), fetched_excerpts)}

    raise ValueError("Researcher agent failed: exhausted retries")


def _target_terms(lesson_plan: dict[str, Any], topic: object) -> list[str]:
    """Terms the fetched evidence must corroborate: topic + learning-objective words."""
    terms = [str(topic)]
    objectives = lesson_plan.get("learning_objectives", [])
    if isinstance(objectives, list):
        for item in objectives:
            if isinstance(item, str):
                terms.append(item)
            elif isinstance(item, dict):
                for key in ("description", "objective", "text"):
                    value = item.get(key)
                    if isinstance(value, str):
                        terms.append(value)
    return terms


def _apply_deterministic_verification(bundle: dict[str, Any], target_terms: list[str]) -> dict[str, Any]:
    """Replace LLM-rated / fabricated credibility with code-computed triangulation.

    A source is VERIFIED only when ≥2 independent domains corroborate the target terms;
    credibility is heuristic (TLD/fetch/coverage/agreement). Sources without a fetched
    body cannot be VERIFIED — no fabrication.
    """
    from packages.agents.sub_agents.researcher.triangulation import (
        FetchedSource,
        heuristic_credibility,
        registrable_domain,
        triangulate,
    )

    sources = bundle.get("sources")
    if not isinstance(sources, list) or not sources:
        return bundle
    fetched = [
        FetchedSource(
            title=str(source.get("title", "")),
            url=source.get("url") if isinstance(source.get("url"), str) else None,
            excerpt=str(source.get("excerpt") or ""),
        )
        for source in sources
    ]
    triangulated = triangulate(fetched, target_terms)
    corroborating_count = len(
        {registrable_domain(t.source.url) for t in triangulated if t.covers and registrable_domain(t.source.url)}
    )
    for source, result in zip(sources, triangulated, strict=False):
        if not isinstance(source, dict):
            continue
        source["verification_status"] = result.verification_status
        source["credibility_score"] = heuristic_credibility(
            source.get("url"),
            covers=result.covers,
            corroborating_count=corroborating_count if result.covers else 0,
            fetched=bool(source.get("excerpt")),
        )
    return bundle


def _finalize_bundle(
    bundle: dict[str, Any],
    fetched_excerpts: dict[str, str],
    target_terms: list[str],
) -> dict[str, Any]:
    return _apply_deterministic_verification(_attach_excerpts(bundle, fetched_excerpts), target_terms)


def _excerpts_by_url(research_evidence: list[dict[str, Any]]) -> dict[str, str]:
    """Map source URL -> fetched excerpt for successfully FETCHED evidence only."""
    mapping: dict[str, str] = {}
    for entry in research_evidence:
        if entry.get("fetch_status") != "FETCHED":
            continue
        source = entry.get("source")
        excerpt = entry.get("excerpt")
        if isinstance(source, dict) and isinstance(excerpt, str) and excerpt:
            url = source.get("url")
            if isinstance(url, str) and url:
                mapping[url] = excerpt
    return mapping


def _attach_excerpts(bundle: dict[str, Any], excerpts: dict[str, str]) -> dict[str, Any]:
    """Attach fetched excerpts to bundle sources by URL (deterministic, no fabrication).

    Only fills excerpts we actually fetched; sources without a fetched body keep
    ``excerpt=None`` so downstream can distinguish grounded from ungrounded sources.
    """
    for source in bundle.get("sources", []):
        if not isinstance(source, dict):
            continue
        if source.get("excerpt"):
            continue
        url = source.get("url")
        if isinstance(url, str) and url in excerpts:
            source["excerpt"] = excerpts[url]
    return bundle


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
