from __future__ import annotations

from typing import Any


def target_terms(lesson_plan: dict[str, Any], topic: object) -> list[str]:
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


def finalize_bundle(
    bundle: dict[str, Any],
    fetched_excerpts: dict[str, str],
    terms: list[str],
) -> dict[str, Any]:
    return _apply_deterministic_verification(attach_excerpts(bundle, fetched_excerpts), terms)


def excerpts_by_url(research_evidence: list[dict[str, Any]]) -> dict[str, str]:
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


def attach_excerpts(bundle: dict[str, Any], excerpts: dict[str, str]) -> dict[str, Any]:
    for source in bundle.get("sources", []):
        if not isinstance(source, dict):
            continue
        if source.get("excerpt"):
            continue
        url = source.get("url")
        if isinstance(url, str) and url in excerpts:
            source["excerpt"] = excerpts[url]
    return bundle


def remember_verified_sources(memory_key: object, bundle: dict[str, Any]) -> None:
    from packages.agents.sub_agents.researcher.grounding import (
        RESEARCH_MEMORY_CACHE,
        utc_now,
        verified_sources_for_cache,
    )

    sources = verified_sources_for_cache(bundle.get("sources"))
    if sources:
        RESEARCH_MEMORY_CACHE.store(memory_key, sources, utc_now())


def _apply_deterministic_verification(bundle: dict[str, Any], terms: list[str]) -> dict[str, Any]:
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
    triangulated = triangulate(fetched, terms)
    corroborating_count = len(
        {registrable_domain(result.source.url) for result in triangulated if result.covers and registrable_domain(result.source.url)}
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
