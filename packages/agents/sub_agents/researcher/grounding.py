from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
import re


class ClaimCriticality(StrEnum):
    CRITICAL = "critical"
    MINOR = "minor"
    SKIP = "skip"


class ClaimVerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    CONTRADICTED = "CONTRADICTED"
    UNVERIFIED = "UNVERIFIED"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True, slots=True)
class TargetClaim:
    text: str
    criticality: ClaimCriticality


@dataclass(frozen=True, slots=True)
class ResearchPolicyRigor:
    min_independent_sources: int
    claim_coverage: float
    sources_per_claim_cap: int
    recency_days: int


@dataclass(frozen=True, slots=True)
class GroundingCacheKey:
    topic: str
    grade: str
    locale: str


@dataclass(frozen=True, slots=True)
class GroundingCacheEntry:
    sources: tuple[dict[str, str], ...]
    stored_at: datetime


class ResearchMemoryCache:
    def __init__(self) -> None:
        self._entries: dict[GroundingCacheKey, GroundingCacheEntry] = {}

    def store(self, key: GroundingCacheKey, sources: tuple[dict[str, str], ...], now: datetime) -> None:
        self._entries[key] = GroundingCacheEntry(sources=sources, stored_at=now)

    def get(self, key: GroundingCacheKey, *, now: datetime, recency_days: int) -> tuple[dict[str, str], ...] | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if now - entry.stored_at > timedelta(days=recency_days):
            del self._entries[key]
            return None
        return entry.sources


RESEARCH_MEMORY_CACHE = ResearchMemoryCache()


def policy_rigor(policy: str, subject: str) -> ResearchPolicyRigor:
    recency_days = 365 if subject.lower() in {"science", "technology", "ict"} else 1825
    match policy:
        case "basic":
            return ResearchPolicyRigor(2, 0.5, 3, recency_days)
        case "rigorous":
            return ResearchPolicyRigor(3, 0.9, 10, recency_days)
        case "standard":
            return ResearchPolicyRigor(2, 0.8, 5, recency_days)
        case _:
            return ResearchPolicyRigor(2, 0.8, 5, recency_days)


def target_claims_from_lesson_plan(lesson_plan: dict[str, object]) -> list[TargetClaim]:
    claims: list[TargetClaim] = []
    topic = lesson_plan.get("topic")
    if isinstance(topic, str) and topic.strip():
        claims.append(TargetClaim(topic.strip(), ClaimCriticality.CRITICAL))
    objectives = lesson_plan.get("learning_objectives")
    if isinstance(objectives, list):
        for item in objectives:
            claim = _objective_claim(item)
            if claim is not None:
                claims.append(claim)
    return claims


def _objective_claim(value: object) -> TargetClaim | None:
    if isinstance(value, str):
        return _classify_claim(value)
    if isinstance(value, dict):
        raw = value.get("description") or value.get("objective") or value.get("text")
        if isinstance(raw, str):
            return _classify_claim(raw)
    return None


def _classify_claim(text: str) -> TargetClaim | None:
    clean = " ".join(text.split())
    if clean == "":
        return None
    lowered = clean.lower()
    if lowered.startswith(("students will", "learners will", "học sinh")):
        return TargetClaim(clean, ClaimCriticality.SKIP)
    if _has_critical_marker(clean):
        return TargetClaim(clean, ClaimCriticality.CRITICAL)
    return TargetClaim(clean, ClaimCriticality.MINOR)


def _has_critical_marker(text: str) -> bool:
    return bool(re.search(r"\b\d{2,}\b|%|=|\bformula\b|\bdefinition\b|\bđịnh nghĩa\b", text, re.IGNORECASE))


def cache_key(topic: object, class_info: object) -> GroundingCacheKey:
    grade = "unknown"
    locale = "vi"
    if isinstance(class_info, dict):
        raw_grade = class_info.get("grade") or class_info.get("grade_level")
        raw_locale = class_info.get("language") or class_info.get("locale")
        grade = str(raw_grade) if raw_grade is not None else grade
        locale = str(raw_locale) if raw_locale is not None else locale
    return GroundingCacheKey(topic=str(topic), grade=grade, locale=locale)


def verified_sources_for_cache(sources: object) -> tuple[dict[str, str], ...]:
    if not isinstance(sources, list):
        return ()
    verified: list[dict[str, str]] = []
    for source in sources:
        if not isinstance(source, dict) or source.get("verification_status") != "VERIFIED":
            continue
        url = source.get("url")
        excerpt = source.get("excerpt")
        title = source.get("title")
        if isinstance(url, str) and isinstance(excerpt, str) and isinstance(title, str):
            verified.append({"title": title, "url": url, "excerpt": excerpt, "verification_status": "VERIFIED"})
    return tuple(verified)


def utc_now() -> datetime:
    return datetime.now(UTC)
