"""Deterministic tests for researcher-001 excerpt persistence (no LLM).

The fetched source body is the grounding corpus Layer-2 fact_check consumes. These
tests assert the researcher persists it into the bundle instead of dropping it into
the prompt only (the pre-2026-07-01 behaviour that starved fact_check).
"""

from __future__ import annotations

from packages.agents.sub_agents.researcher.runtime_grounding import attach_excerpts, excerpts_by_url


def test_excerpts_by_url_keeps_only_fetched_bodies() -> None:
    evidence = [
        {"source": {"url": "https://a.edu"}, "fetch_status": "FETCHED", "excerpt": "body A"},
        {"source": {"url": "https://b.gov"}, "fetch_status": "FAILED", "excerpt": ""},
        {"source": {"url": "https://c.org"}, "fetch_status": "SKIPPED", "excerpt": ""},
        {"source": {"url": ""}, "fetch_status": "FETCHED", "excerpt": "no url"},
    ]

    assert excerpts_by_url(evidence) == {"https://a.edu": "body A"}


def test_attach_excerpts_fills_matching_sources_only() -> None:
    bundle = {
        "sources": [
            {"title": "A", "url": "https://a.edu", "excerpt": None},
            {"title": "B", "url": "https://b.gov", "excerpt": None},
            {"title": "C", "url": "https://c.org", "excerpt": "already here"},
        ]
    }

    result = attach_excerpts(bundle, {"https://a.edu": "body A", "https://z.edu": "unused"})

    sources = {s["title"]: s.get("excerpt") for s in result["sources"]}
    assert sources["A"] == "body A"  # filled from fetched corpus
    assert sources["B"] is None  # not fetched -> stays ungrounded (no fabrication)
    assert sources["C"] == "already here"  # pre-existing excerpt preserved
