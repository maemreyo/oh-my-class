from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from common.contracts.research_brief import (
    ArtifactResearchGuidance,
    EvidenceCitation,
    PrePlanningSearchBrief,
    ResearchBrief,
)
from services.gateway.research_safety import evidence_terms, scrub_text
from services.gateway.research_urls import domain_for, normalize_url

if TYPE_CHECKING:
    from common.contracts.run_contract import RunContract

MATH_SUBJECTS: Final = frozenset({"math", "toán", "toan"})
ENGLISH_SUBJECTS: Final = frozenset({"english", "esl"})


@dataclass(frozen=True, slots=True)
class SearchQuery:
    query: str
    purpose: str


@dataclass(frozen=True, slots=True)
class SearchPlan:
    queries: tuple[SearchQuery, ...]
    requires_confirmation: bool
    confirmation_reasons: tuple[str, ...]
    brief: PrePlanningSearchBrief


@dataclass(frozen=True, slots=True)
class SearchCandidate:
    title: str
    url: str
    snippet: str


@dataclass(frozen=True, slots=True)
class NormalizedSearchCandidate:
    title: str
    normalized_url: str
    domain: str
    snippet: str


@dataclass(frozen=True, slots=True)
class RankedSearchCandidate:
    source_id: str
    title: str
    url: str
    domain: str
    credibility_score: float


@dataclass(frozen=True, slots=True)
class FetchResult:
    source_id: str
    content: str


@dataclass(frozen=True, slots=True)
class ExtractedEvidence:
    source_id: str
    snippet: str


def plan_search(contract: RunContract) -> SearchPlan:
    queries = _queries_for(contract)
    reasons = _confirmation_reasons(contract, len(queries))
    return SearchPlan(
        queries=queries,
        requires_confirmation=bool(reasons),
        confirmation_reasons=reasons,
        brief=PrePlanningSearchBrief(
            topic=contract.topic,
            subject=contract.subject,
            risk_level="medium" if reasons else "low",
            query_count=len(queries),
            confirmation_reasons=reasons,
        ),
    )


def normalize_search_candidates(
    candidates: tuple[SearchCandidate, ...],
    *,
    blocked_domains: frozenset[str],
) -> tuple[NormalizedSearchCandidate, ...]:
    seen: set[str] = set()
    normalized: list[NormalizedSearchCandidate] = []
    for candidate in candidates:
        url = normalize_url(candidate.url)
        domain = domain_for(url)
        if domain in blocked_domains or url in seen:
            continue
        seen.add(url)
        normalized.append(
            NormalizedSearchCandidate(
                title=candidate.title,
                normalized_url=url,
                domain=domain,
                snippet=candidate.snippet,
            ),
        )
    return tuple(normalized)


def rank_search_candidates(
    candidates: tuple[NormalizedSearchCandidate, ...],
    *,
    teacher_sources: frozenset[str],
    preferred_domains: frozenset[str],
    max_per_domain: int,
) -> tuple[RankedSearchCandidate, ...]:
    sorted_candidates = sorted(
        candidates,
        key=lambda candidate: _score(candidate, teacher_sources, preferred_domains),
        reverse=True,
    )
    domain_counts: dict[str, int] = {}
    ranked: list[RankedSearchCandidate] = []
    for candidate in sorted_candidates:
        count = domain_counts.get(candidate.domain, 0)
        if count >= max_per_domain:
            continue
        domain_counts[candidate.domain] = count + 1
        ranked.append(
            RankedSearchCandidate(
                source_id=f"source-{len(ranked) + 1}",
                title=candidate.title,
                url=candidate.normalized_url,
                domain=candidate.domain,
                credibility_score=_score(candidate, teacher_sources, preferred_domains),
            ),
        )
    return tuple(ranked)


def extract_evidence(
    fetches: tuple[FetchResult, ...],
    ranked_candidates: tuple[RankedSearchCandidate, ...],
) -> tuple[ExtractedEvidence, ...]:
    allowed = {candidate.source_id for candidate in ranked_candidates}
    evidence: list[ExtractedEvidence] = []
    for fetch in fetches:
        if fetch.source_id not in allowed or fetch.content.strip() == "":
            continue
        evidence.append(
            ExtractedEvidence(source_id=fetch.source_id, snippet=_compact_snippet(fetch.content)),
        )
    return tuple(evidence)


def build_research_brief(
    *,
    topic: str,
    subject: str,
    evidence: tuple[ExtractedEvidence, ...],
    ranked_candidates: tuple[RankedSearchCandidate, ...],
) -> ResearchBrief:
    cited = [
        candidate for candidate in ranked_candidates if _has_evidence(candidate.source_id, evidence)
    ]
    citation_ids = [candidate.source_id for candidate in cited]
    return ResearchBrief(
        topic=topic,
        subject=subject,
        key_findings=[item.snippet for item in evidence],
        citations=[
            EvidenceCitation(
                source_id=candidate.source_id,
                title=candidate.title,
                url=candidate.url,
                domain=candidate.domain,
                credibility_score=candidate.credibility_score,
            )
            for candidate in cited
        ],
        artifact_guidance=[
            ArtifactResearchGuidance(
                artifact_type="shared",
                guidance=["Use only cited findings from the compact research brief."],
                citation_ids=citation_ids,
            ),
        ],
    )


def _queries_for(contract: RunContract) -> tuple[SearchQuery, ...]:
    topic = scrub_text(contract.topic)
    subject = contract.subject.lower()
    evidence = evidence_terms(contract.student_evidence)
    if subject in MATH_SUBJECTS:
        return (
            SearchQuery(
                f"{topic} grade {contract.grade_band} math misconceptions",
                "misconceptions",
            ),
            SearchQuery(f"{topic} {evidence} teaching intervention".strip(), "intervention"),
        )
    if subject in ENGLISH_SUBJECTS:
        return (
            SearchQuery(f"{topic} ESL lesson common learner errors", "language_errors"),
            SearchQuery(f"{topic} {contract.instruction_language} scaffolded practice", "scaffold"),
        )
    return (
        SearchQuery(f"{topic} {contract.subject} key concepts", "concepts"),
        SearchQuery(f"{topic} classroom examples citations", "examples"),
    )


def _confirmation_reasons(contract: RunContract, query_count: int) -> tuple[str, ...]:
    reasons: list[str] = []
    if contract.locale == "vi-VN" and contract.curriculum is None:
        reasons.append("ambiguous_curriculum")
    if query_count > 5:
        reasons.append("high_budget")
    return tuple(reasons)


def _score(
    candidate: NormalizedSearchCandidate,
    teacher_sources: frozenset[str],
    preferred_domains: frozenset[str],
) -> float:
    score = 0.4
    if candidate.normalized_url in {normalize_url(url) for url in teacher_sources}:
        score += 0.4
    if candidate.domain in preferred_domains:
        score += 0.2
    return min(score + min(len(candidate.snippet), 100) / 1000, 1.0)


def _compact_snippet(content: str) -> str:
    first_sentence = content.strip().split(".", maxsplit=1)[0].strip()
    return f"{first_sentence}."[:240]


def _has_evidence(source_id: str, evidence: tuple[ExtractedEvidence, ...]) -> bool:
    return any(item.source_id == source_id for item in evidence)
