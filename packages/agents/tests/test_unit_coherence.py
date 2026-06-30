"""Tests for cross-session coherence lint (td-016).

Deterministic checks don't need a real LLM.
LLM-based terminology drift test uses a mock client.
"""

from __future__ import annotations

import asyncio

import pytest

from common.contracts.lesson_sequence import (
    KnowledgeComponent,
    SessionPlan,
)
from packages.agents.quality.unit_coherence import (
    CoherenceWarningType,
    check_non_monotonic_difficulty,
    check_redundant_coverage,
    check_unresolved_back_references,
    run_coherence_lint,
)


# "concept_map" is the correct string literal for MethodologyTag.
_METHODOLOGY = "concept_map"


def _sess(
    session_id: str,
    order_index: int,
    *,
    bloom: str = "understand",
    sub_topic: str | None = None,
    objectives: list[str] | None = None,
    title: str | None = None,
    kcs: list[str] | None = None,
) -> SessionPlan:
    kc_list = [
        KnowledgeComponent(kc_id=kc_id, title=kc_id.replace("-", " "), description="desc")
        for kc_id in (kcs or [])
    ]
    return SessionPlan(
        session_id=session_id,
        order_index=order_index,
        title=title or f"Session {session_id}",
        sub_topic=sub_topic or f"Sub-topic {session_id}",
        duration_minutes=30,
        learning_objectives=objectives or ["Objective"],
        bloom_level_primary=bloom,
        methodology_primary=_METHODOLOGY,
        knowledge_components=kc_list,
    )


# ---------------------------------------------------------------------------
# Back-reference checks
# ---------------------------------------------------------------------------


class TestUnresolvedBackReferences:
    def test_detects_english_back_reference(self) -> None:
        """session with an objective referencing session 12 that does not exist."""
        sessions = [
            _sess("s1", 1, title="Intro"),
            _sess("s9", 9, objectives=["Apply as learned in session 12"]),
        ]
        warnings = check_unresolved_back_references(sessions)
        w_types = [w.warning_type for w in warnings]
        assert CoherenceWarningType.UNRESOLVED_BACK_REFERENCE in w_types

    def test_detects_vietnamese_back_reference(self) -> None:
        """Vietnamese back-reference pattern "đã học ở buổi N" is detected."""
        sessions = [
            _sess("s1", 1),
            _sess("s2", 2, objectives=["đã học ở buổi 99"]),
        ]
        warnings = check_unresolved_back_references(sessions)
        assert any(w.warning_type == CoherenceWarningType.UNRESOLVED_BACK_REFERENCE for w in warnings)

    def test_no_warning_for_resolved_reference(self) -> None:
        """Reference to session 1 resolves because order_index 1 exists."""
        sessions = [
            _sess("s1", 1, objectives=["as learned in session 1"]),
            _sess("s2", 2),
        ]
        warnings = check_unresolved_back_references(sessions)
        assert not warnings

    def test_no_warning_for_no_references(self) -> None:
        """Sequences without any back-reference patterns produce no warnings."""
        sessions = [_sess("s1", 1), _sess("s2", 2)]
        warnings = check_unresolved_back_references(sessions)
        assert not warnings

    def test_unresolved_back_reference_warning(self) -> None:
        """Title containing 'as learned in session 9' when no session 9 exists → warning."""
        sessions = [
            _sess("s1", 1),
            _sess("s2", 2, title="Review as learned in session 9"),
        ]
        warnings = check_unresolved_back_references(sessions)
        assert any(
            w.warning_type == CoherenceWarningType.UNRESOLVED_BACK_REFERENCE
            for w in warnings
        )


# ---------------------------------------------------------------------------
# Non-monotonic difficulty checks
# ---------------------------------------------------------------------------


class TestNonMonotonicDifficulty:
    def test_detects_significant_bloom_drop(self) -> None:
        """analyze → remember is a drop of 3 ranks — must produce a warning."""
        sessions = [
            _sess("s1", 1, bloom="analyze"),
            _sess("s2", 2, bloom="remember"),
        ]
        warnings = check_non_monotonic_difficulty(sessions)
        assert any(w.warning_type == CoherenceWarningType.NON_MONOTONIC_DIFFICULTY for w in warnings)
        assert any("s1" in w.involved_session_ids and "s2" in w.involved_session_ids for w in warnings)

    def test_non_monotonic_difficulty_warning(self) -> None:
        """session 3 has bloom=remember after session 1 bloom=analyze → warning."""
        sessions = [
            _sess("s1", 1, bloom="analyze"),
            _sess("s2", 2, bloom="understand"),
            _sess("s3", 3, bloom="remember"),
        ]
        warnings = check_non_monotonic_difficulty(sessions)
        # analyze → understand is a drop of 2 ranks → flagged
        assert any(w.warning_type == CoherenceWarningType.NON_MONOTONIC_DIFFICULTY for w in warnings)

    def test_no_warning_for_monotonic_progression(self) -> None:
        """A sequence strictly ascending in Bloom rank produces no warnings."""
        sessions = [
            _sess("s1", 1, bloom="remember"),
            _sess("s2", 2, bloom="understand"),
            _sess("s3", 3, bloom="apply"),
            _sess("s4", 4, bloom="analyze"),
        ]
        warnings = check_non_monotonic_difficulty(sessions)
        assert not warnings

    def test_no_warning_for_small_drop(self) -> None:
        """Dropping exactly 1 rank is allowed (spiral review pattern)."""
        sessions = [
            _sess("s1", 1, bloom="understand"),
            _sess("s2", 2, bloom="remember"),  # drop of 1 → no warning
        ]
        warnings = check_non_monotonic_difficulty(sessions)
        assert not warnings


# ---------------------------------------------------------------------------
# Redundant coverage checks
# ---------------------------------------------------------------------------


class TestRedundantCoverage:
    def test_detects_same_sub_topic(self) -> None:
        """Two sessions differing only by case produce a REDUNDANT_COVERAGE warning."""
        sessions = [
            _sess("s1", 1, sub_topic="Phân số"),
            _sess("s2", 2, sub_topic="phân số"),  # same after normalisation
        ]
        warnings = check_redundant_coverage(sessions)
        assert any(w.warning_type == CoherenceWarningType.REDUNDANT_COVERAGE for w in warnings)
        assert any("s1" in w.involved_session_ids and "s2" in w.involved_session_ids for w in warnings)

    def test_redundant_coverage_warning(self) -> None:
        """Exact duplicate sub_topic between two sessions → REDUNDANT_COVERAGE."""
        sessions = [
            _sess("s1", 1, sub_topic="Fractions"),
            _sess("s2", 2, sub_topic="Fractions"),
        ]
        warnings = check_redundant_coverage(sessions)
        assert any(w.warning_type == CoherenceWarningType.REDUNDANT_COVERAGE for w in warnings)

    def test_no_warning_for_distinct_topics(self) -> None:
        """Distinct sub_topics produce no redundancy warnings."""
        sessions = [
            _sess("s1", 1, sub_topic="Phân số"),
            _sess("s2", 2, sub_topic="Số thập phân"),
        ]
        warnings = check_redundant_coverage(sessions)
        assert not warnings


# ---------------------------------------------------------------------------
# run_coherence_lint integration
# ---------------------------------------------------------------------------


class TestRunCoherenceLint:
    def test_clean_sequence_no_warnings(self) -> None:
        """A well-structured ascending sequence produces no deterministic warnings."""
        sessions = [
            _sess("s1", 1, bloom="remember", sub_topic="Phân số cơ bản"),
            _sess("s2", 2, bloom="understand", sub_topic="Phân số bằng nhau"),
            _sess("s3", 3, bloom="apply", sub_topic="Cộng trừ phân số"),
            _sess("s4", 4, bloom="analyze", sub_topic="Phân số trong bài toán thực tế"),
        ]
        warnings = asyncio.run(run_coherence_lint(sessions, llm_client=None))
        assert not warnings

    def test_unit_complete_with_warnings(self) -> None:
        """run_coherence_lint must never raise — unit remains exportable even with warnings."""
        sessions = [
            _sess("s1", 1, bloom="analyze"),
            _sess("s2", 2, bloom="remember"),  # non-monotonic drop
        ]
        # Must not raise
        warnings = asyncio.run(run_coherence_lint(sessions, llm_client=None))
        # Warnings are returned but no exception is raised
        assert isinstance(warnings, list)

    def test_terminology_drift_skipped_without_llm(self) -> None:
        """Without llm_client, terminology drift check is a no-op returning []."""
        sessions = [_sess("s1", 1, sub_topic="tỉ số"), _sess("s2", 2, sub_topic="phân số")]
        warnings = asyncio.run(run_coherence_lint(sessions, llm_client=None))
        drift_warnings = [w for w in warnings if w.warning_type == CoherenceWarningType.TERMINOLOGY_DRIFT]
        assert not drift_warnings

    @pytest.mark.real_llm
    async def test_terminology_warning_same_concept_diff_terms(self) -> None:
        """Mock LLM returns a known response → CoherenceWarning naming both sessions."""

        class MockLLMClient:
            async def acomplete(self, prompt: str) -> str:
                return (
                    "session_s1 and session_s2 use different terms for the same concept: "
                    "tỉ số vs phân số"
                )

        sessions = [
            _sess("s1", 1, sub_topic="Phân số", kcs=["phan-so"]),
            _sess("s2", 2, sub_topic="Tỉ số và tỉ lệ", kcs=["ti-so"]),
        ]
        warnings = await run_coherence_lint(sessions, llm_client=MockLLMClient())
        drift = [w for w in warnings if w.warning_type == CoherenceWarningType.TERMINOLOGY_DRIFT]
        assert drift, f"Expected terminology drift warning, got: {warnings}"
        assert "s1" in drift[0].involved_session_ids or "s2" in drift[0].involved_session_ids
