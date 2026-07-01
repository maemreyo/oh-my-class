"""FACT Protocol — Find → Assess → Cross-reference → Tag.

Hallucination detection for factual claims in generated content.
Every HIGH-risk claim must be verified against ≥2 independent sources.

Tag values:
- VERIFIED: Confirmed by 2+ sources
- MODIFIED: Partially confirmed, adjusted for accuracy
- REMOVED: Could not be verified, flagged for removal
- UNCERTAIN: Insufficient sources to verify
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypedDict


class VerificationTag(StrEnum):
    """Tag for factual claim verification status."""

    VERIFIED = "VERIFIED"
    MODIFIED = "MODIFIED"
    REMOVED = "REMOVED"
    UNCERTAIN = "UNCERTAIN"


@dataclass(frozen=True, slots=True)
class VerifiedClaim:
    """A factual claim with its verification status."""

    claim: str
    tag: VerificationTag
    sources: list[dict[str, str]] = field(default_factory=list)
    confidence: float = 0.0  # 0.0–1.0


class SourceDocument(TypedDict, total=False):
    title: str
    content: str
    url: str


class AssessedSource(SourceDocument):
    relevance: float


class FACTChecker:
    """Implements the FACT protocol for hallucination detection.

    Usage:
        checker = FACTChecker(min_sources=2)
        results = await checker.check_claims(content, sources)
    """

    def __init__(self, *, min_sources: int = 2) -> None:
        self.min_sources = min_sources

    async def find_claims(self, content: str) -> list[str]:
        """Extract factual claims from content.

        Args:
            content: Text content to analyze.

        Returns:
            List of extracted factual claims.
        """
        sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", content) if sentence.strip()]
        return [sentence for sentence in sentences if _has_factual_marker(sentence)]

    async def assess_sources(
        self,
        claim: str,
        sources: list[SourceDocument],
    ) -> list[AssessedSource]:
        """Assess source credibility for a claim.

        Args:
            claim: Factual claim to verify.
            sources: List of source documents.

        Returns:
            Assessed sources with credibility scores.
        """
        assessed: list[AssessedSource] = []
        for source in sources:
            content = source.get("content", "")
            relevance = _claim_relevance(claim, content)
            if relevance > 0.0:
                assessed.append({**source, "relevance": relevance})
        return sorted(assessed, key=lambda item: item["relevance"], reverse=True)

    async def cross_reference(
        self,
        claim: str,
        assessed_sources: list[AssessedSource],
    ) -> VerificationTag:
        """Cross-reference claim against assessed sources.

        Args:
            claim: Factual claim.
            assessed_sources: Sources with credibility scores.

        Returns:
            VerificationTag indicating verification status.
        """
        if not claim.strip():
            return VerificationTag.UNCERTAIN
        matching_sources = [source for source in assessed_sources if source["relevance"] >= 0.8]
        if len(matching_sources) >= self.min_sources:
            return VerificationTag.VERIFIED
        return VerificationTag.UNCERTAIN

    async def check_claims(
        self,
        content: str,
        sources: list[SourceDocument],
    ) -> list[VerifiedClaim]:
        """Run the full FACT protocol on content.

        Args:
            content: Text content to verify.
            sources: Available sources for cross-referencing.

        Returns:
            List of VerifiedClaim with tags and sources.
        """
        claims = await self.find_claims(content)
        verified: list[VerifiedClaim] = []
        for claim in claims:
            assessed = await self.assess_sources(claim, sources)
            tag = await self.cross_reference(claim, assessed)
            matching_sources = [source for source in assessed if source["relevance"] >= 0.8]
            verified.append(VerifiedClaim(
                claim=claim,
                tag=tag,
                sources=[_public_source(source) for source in matching_sources[: self.min_sources]],
                confidence=1.0 if tag is VerificationTag.VERIFIED else 0.0,
            ))
        return verified


def _has_factual_marker(sentence: str) -> bool:
    return bool(re.search(r"\b\d{4}\b|\b\d+(?:\.\d+)?%\b|\b[A-Z][a-z]*\d+[A-Z0-9]*\b", sentence))


def _claim_relevance(claim: str, source_content: str) -> float:
    claim_terms = _terms(claim)
    if not claim_terms:
        return 0.0
    source_terms = _terms(source_content)
    overlap = len(claim_terms & source_terms) / len(claim_terms)
    return 1.0 if overlap >= 0.8 else round(overlap, 2)


def _terms(value: str) -> frozenset[str]:
    return frozenset(re.findall(r"[a-z0-9]+", value.lower()))


def _public_source(source: AssessedSource) -> dict[str, str]:
    return {
        key: value
        for key in ("title", "content", "url")
        if isinstance((value := source.get(key)), str)
    }
