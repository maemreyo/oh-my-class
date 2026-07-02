"""Deterministic ≥2-source triangulation — the core of researcher-001.

A source is ``VERIFIED`` only when **≥2 independent sources corroborate the same target
terms** — computed by code from fetched evidence, never an LLM-rated credibility number.
Independence = distinct registrable domain (two pages from one site are not independent).
This is the shared mechanism behind both the Layer-2 fact_check corpus and vocabulary
lexical grounding (one mechanism, two consumers).

Deterministic and LLM-free by design so it can be unit-tested exhaustively.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urlparse

DEFAULT_COVERAGE_THRESHOLD = 0.8
DEFAULT_MIN_INDEPENDENT = 2


@dataclass(frozen=True, slots=True)
class FetchedSource:
    """A fetched candidate source with its extracted body."""

    title: str
    url: str | None
    excerpt: str


@dataclass(frozen=True, slots=True)
class TriangulatedSource:
    """A source with a code-derived verification verdict."""

    source: FetchedSource
    verification_status: str  # "VERIFIED" | "UNCERTAIN"
    covers: bool
    corroborating_domains: tuple[str, ...]


def registrable_domain(url: str | None) -> str:
    """Best-effort registrable domain (last two labels of the host)."""
    if not url:
        return ""
    netloc = urlparse(url).netloc.lower()
    host = netloc.split("@")[-1].split(":")[0]
    labels = [label for label in host.split(".") if label]
    if len(labels) < 2:
        return host
    return ".".join(labels[-2:])


def heuristic_credibility(
    url: str | None,
    *,
    covers: bool,
    corroborating_count: int,
    fetched: bool,
) -> float:
    """Credibility from source-type/TLD, fetch success, coverage, and agreement count.

    Computed — never an LLM-rated or fabricated constant (the pre-2026-07-01 fallback
    hardcoded 0.3/0.5). Bounded to [0, 1].
    """
    score = 0.3
    domain = registrable_domain(url)
    if domain.endswith((".edu", ".gov")):
        score += 0.3
    elif domain.endswith((".org", ".int")):
        score += 0.15
    if fetched:
        score += 0.1
    if covers:
        score += 0.1
    score += min(0.2, 0.1 * max(0, corroborating_count - 1))
    return round(min(1.0, max(0.0, score)), 2)


def _tokens(text: str) -> frozenset[str]:
    return frozenset(re.findall(r"[a-z0-9]+", text.lower()))


def _target_tokens(target_terms: Iterable[str]) -> frozenset[str]:
    tokens: set[str] = set()
    for term in target_terms:
        tokens |= _tokens(term)
    return frozenset(tokens)


def _covers(excerpt: str, targets: frozenset[str], threshold: float) -> bool:
    if not targets:
        return False
    excerpt_tokens = _tokens(excerpt)
    overlap = len(targets & excerpt_tokens) / len(targets)
    return overlap >= threshold


def triangulate(
    sources: Iterable[FetchedSource],
    target_terms: Iterable[str],
    *,
    min_independent: int = DEFAULT_MIN_INDEPENDENT,
    coverage_threshold: float = DEFAULT_COVERAGE_THRESHOLD,
) -> list[TriangulatedSource]:
    """Verify sources by independent-domain corroboration of the target terms.

    A source ``covers`` the target when its excerpt contains at least
    ``coverage_threshold`` of the target tokens. A covering source is ``VERIFIED`` only
    when ``≥ min_independent`` **distinct domains** cover the target; otherwise every
    source is ``UNCERTAIN`` (no fabrication, no single-source promotion).
    """
    targets = _target_tokens(target_terms)
    source_list = list(sources)

    covering = [source for source in source_list if _covers(source.excerpt, targets, coverage_threshold)]
    corroborating_domains = tuple(
        sorted({domain for source in covering if (domain := registrable_domain(source.url))})
    )
    corroborated = len(corroborating_domains) >= min_independent

    results: list[TriangulatedSource] = []
    for source in source_list:
        covers = _covers(source.excerpt, targets, coverage_threshold)
        status = "VERIFIED" if covers and corroborated else "UNCERTAIN"
        results.append(
            TriangulatedSource(
                source=source,
                verification_status=status,
                covers=covers,
                corroborating_domains=corroborating_domains if covers else (),
            )
        )
    return results
