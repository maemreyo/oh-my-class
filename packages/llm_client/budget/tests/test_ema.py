"""Tests for EMATracker — exponential moving average per task."""
from __future__ import annotations

from packages.llm_client.budget.ema import EMATracker


def test_ema_returns_none_before_min_samples():
    tracker = EMATracker(alpha=0.1, min_samples=3)
    tracker.record("content_generation", 8000)
    tracker.record("content_generation", 9000)
    assert tracker.get_ema("content_generation") is None  # only 2 samples


def test_ema_returns_value_after_min_samples():
    tracker = EMATracker(alpha=0.1, min_samples=3)
    for tokens in [8000, 9000, 7500]:
        tracker.record("content_generation", tokens)
    assert tracker.get_ema("content_generation") is not None


def test_ema_adapts_toward_new_values():
    tracker = EMATracker(alpha=0.5, min_samples=1)
    tracker.record("task", 1000)
    tracker.record("task", 2000)  # alpha=0.5: new value pulls strongly
    ema = tracker.get_ema("task")
    assert ema is not None
    assert 1000 < ema < 2000


def test_ema_first_record_sets_initial_value():
    tracker = EMATracker(alpha=0.1, min_samples=1)
    tracker.record("task", 5000)
    assert tracker.get_ema("task") == 5000.0


def test_ema_sample_count_increments():
    tracker = EMATracker(alpha=0.1, min_samples=5)
    assert tracker.sample_count("task") == 0
    tracker.record("task", 1000)
    assert tracker.sample_count("task") == 1
    tracker.record("task", 1000)
    assert tracker.sample_count("task") == 2


def test_ema_unknown_task_returns_none():
    tracker = EMATracker(alpha=0.1, min_samples=3)
    assert tracker.get_ema("nonexistent_task") is None


def test_ema_unknown_task_sample_count_is_zero():
    tracker = EMATracker(alpha=0.1, min_samples=3)
    assert tracker.sample_count("nonexistent_task") == 0


def test_ema_tracks_multiple_tasks_independently():
    tracker = EMATracker(alpha=0.5, min_samples=1)
    tracker.record("task_a", 1000)
    tracker.record("task_b", 5000)
    assert tracker.get_ema("task_a") == 1000.0
    assert tracker.get_ema("task_b") == 5000.0


def test_ema_smoothing_with_alpha_01():
    tracker = EMATracker(alpha=0.1, min_samples=1)
    tracker.record("task", 1000)   # initial = 1000
    tracker.record("task", 2000)   # EMA = 0.1*2000 + 0.9*1000 = 200 + 900 = 1100
    ema = tracker.get_ema("task")
    assert ema is not None
    assert abs(ema - 1100.0) < 0.01
