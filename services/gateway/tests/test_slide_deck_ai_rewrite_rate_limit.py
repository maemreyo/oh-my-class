from __future__ import annotations

from datetime import UTC, datetime, timedelta

from services.gateway.slide_deck_ai_rewrite_rate_limit import (
    SlideDeckAiRewriteRateLimitState,
    allow_ai_rewrite_attempt,
)


def test_allows_up_to_the_limit_then_denies() -> None:
    state = SlideDeckAiRewriteRateLimitState()
    now = datetime.now(UTC)

    for _ in range(3):
        assert allow_ai_rewrite_attempt(state, teacher_id="teacher-1", now=now, limit=3, window_seconds=60) is True

    assert allow_ai_rewrite_attempt(state, teacher_id="teacher-1", now=now, limit=3, window_seconds=60) is False


def test_different_teachers_are_independent_buckets() -> None:
    state = SlideDeckAiRewriteRateLimitState()
    now = datetime.now(UTC)

    assert allow_ai_rewrite_attempt(state, teacher_id="teacher-1", now=now, limit=1, window_seconds=60) is True
    assert allow_ai_rewrite_attempt(state, teacher_id="teacher-1", now=now, limit=1, window_seconds=60) is False
    assert allow_ai_rewrite_attempt(state, teacher_id="teacher-2", now=now, limit=1, window_seconds=60) is True


def test_window_expiry_allows_a_retry() -> None:
    state = SlideDeckAiRewriteRateLimitState()
    now = datetime.now(UTC)

    assert allow_ai_rewrite_attempt(state, teacher_id="teacher-1", now=now, limit=1, window_seconds=60) is True
    assert allow_ai_rewrite_attempt(state, teacher_id="teacher-1", now=now, limit=1, window_seconds=60) is False

    later = now + timedelta(seconds=61)
    assert allow_ai_rewrite_attempt(state, teacher_id="teacher-1", now=later, limit=1, window_seconds=60) is True
