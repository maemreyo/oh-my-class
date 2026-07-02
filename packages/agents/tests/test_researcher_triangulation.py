"""Deterministic tests for researcher-001 ≥2-source triangulation (no LLM)."""

from __future__ import annotations

from packages.agents.sub_agents.researcher.triangulation import (
    FetchedSource,
    registrable_domain,
    triangulate,
)

TERMS = ("affect", "effect")
BODY = "Affect is a verb and effect is a noun in most usage."


def _status(results: list, url: str) -> str:
    return next(r.verification_status for r in results if r.source.url == url)


def test_two_independent_domains_corroborate_to_verified() -> None:
    sources = [
        FetchedSource("A", "https://grammar.edu/affect", BODY),
        FetchedSource("B", "https://writing.gov/effect", BODY),
    ]
    results = triangulate(sources, TERMS)
    assert _status(results, "https://grammar.edu/affect") == "VERIFIED"
    assert _status(results, "https://writing.gov/effect") == "VERIFIED"


def test_same_domain_is_not_independent() -> None:
    # Two covering pages from ONE site are not independent -> both UNCERTAIN.
    sources = [
        FetchedSource("A", "https://grammar.edu/affect", BODY),
        FetchedSource("B", "https://grammar.edu/effect", BODY),
    ]
    results = triangulate(sources, TERMS)
    assert {r.verification_status for r in results} == {"UNCERTAIN"}


def test_single_covering_source_is_uncertain() -> None:
    sources = [
        FetchedSource("A", "https://grammar.edu/x", BODY),
        FetchedSource("B", "https://other.org/y", "Unrelated content about weather."),
    ]
    results = triangulate(sources, TERMS)
    assert _status(results, "https://grammar.edu/x") == "UNCERTAIN"  # only 1 independent cover
    assert _status(results, "https://other.org/y") == "UNCERTAIN"  # does not cover


def test_urlless_sources_do_not_count_toward_independence() -> None:
    sources = [
        FetchedSource("A", None, BODY),
        FetchedSource("B", None, BODY),
    ]
    results = triangulate(sources, TERMS)
    assert {r.verification_status for r in results} == {"UNCERTAIN"}


def test_empty_targets_never_verify() -> None:
    results = triangulate([FetchedSource("A", "https://a.edu", BODY)], ())
    assert results[0].verification_status == "UNCERTAIN"
    assert results[0].covers is False


def test_registrable_domain_extraction() -> None:
    assert registrable_domain("https://sub.grammar.edu/path?q=1") == "grammar.edu"
    assert registrable_domain("http://user@host.co:8080/x") == "host.co"
    assert registrable_domain(None) == ""
