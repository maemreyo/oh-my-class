"""Unit tests for the QA-02 load harness's own logic (scripts/load_test_*.py) —
no network, no DB. Covers: request-mix generation is realistic/configurable,
SLO assertion pass/fail on synthetic inputs, the burst profile actually
bursts, and baseline-regression comparison flags a real regression while
ignoring noise within tolerance.
"""
from __future__ import annotations

from pathlib import Path

from scripts.load_test_assert import assert_slo
from scripts.load_test_baseline import (
    BaselineMetrics,
    compare_to_baseline,
    load_baseline,
    save_baseline,
)
from scripts.load_test_profiles import (
    FULL_PROFILE,
    SMOKE_PROFILE,
    LoadProfile,
    RequestMix,
    build_run_payload,
    generate_request_plan,
)

# ── Request-mix generation ────────────────────────────────────────────────


def test_request_mix_must_sum_to_one() -> None:
    import pytest

    with pytest.raises(ValueError):
        RequestMix(generate_pack=0.5, diagnose_then_generate=0.6)


def test_generate_request_plan_respects_configured_mix_ratio() -> None:
    profile = LoadProfile(
        name="mix-check",
        total_requests=400,
        duration_seconds=60.0,
        mix=RequestMix(generate_pack=0.2, diagnose_then_generate=0.8),
    )
    plan = generate_request_plan(profile, seed=42)

    modes = [mode for _offset, mode, _payload in plan]
    diagnose_ratio = modes.count("diagnose_then_generate") / len(modes)

    assert len(plan) == 400
    # Random sampling around an 0.8 target — generous tolerance, this checks
    # "respects the mix" not "matches it to 3 decimal places".
    assert 0.7 < diagnose_ratio < 0.9


def test_payloads_are_realistic_and_vary_by_topic_and_mode() -> None:
    import random

    rng = random.Random(1)
    payloads = [build_run_payload("generate_pack", rng) for _ in range(20)]

    topics = {p["class_info"]["topic"] for p in payloads}
    assert len(topics) > 1, "payload generation should vary topic, not repeat one fixture"
    for payload in payloads:
        assert payload["raw_request"]
        assert payload["class_info"]["grade"] in range(3, 9)
        assert "student_evidence" not in payload["class_info"]

    diagnose_payload = build_run_payload("diagnose_then_generate", random.Random(2))
    assert "student_evidence" in diagnose_payload["class_info"], (
        "diagnose_then_generate is heavier than plain generate — must carry the extra field"
    )


def test_generate_request_plan_is_deterministic_given_a_seed() -> None:
    plan_a = generate_request_plan(SMOKE_PROFILE, seed=7)
    plan_b = generate_request_plan(SMOKE_PROFILE, seed=7)
    assert plan_a == plan_b


def test_smoke_and_full_profiles_are_distinct_scale() -> None:
    assert SMOKE_PROFILE.total_requests < FULL_PROFILE.total_requests
    assert SMOKE_PROFILE.duration_seconds < FULL_PROFILE.duration_seconds
    assert FULL_PROFILE.total_requests == 5000, "must match the ADR-034 north-star peak"


# ── Burst profile actually bursts ─────────────────────────────────────────


def test_burst_window_has_higher_instantaneous_arrival_rate_than_steady_window() -> None:
    profile = LoadProfile(
        name="burst-check",
        total_requests=1000,
        duration_seconds=100.0,
        burst_fraction=0.2,  # last 20s is the burst window
        burst_multiplier=5.0,
    )
    plan = generate_request_plan(profile, seed=3)
    offsets = [offset for offset, _mode, _payload in plan]

    steady_count = sum(1 for o in offsets if o < 80.0)
    burst_count = sum(1 for o in offsets if o >= 80.0)

    steady_rate = steady_count / 80.0
    burst_rate = burst_count / 20.0

    assert burst_rate > steady_rate * 3, (
        f"burst window should be markedly denser: steady_rate={steady_rate:.2f}/s "
        f"burst_rate={burst_rate:.2f}/s"
    )


def test_zero_burst_fraction_yields_uniform_arrivals() -> None:
    profile = LoadProfile(
        name="no-burst", total_requests=200, duration_seconds=50.0, burst_fraction=0.0,
    )
    plan = generate_request_plan(profile, seed=9)
    offsets = [offset for offset, _mode, _payload in plan]
    assert all(0.0 <= o <= 50.0 for o in offsets)


# ── SLO assertion logic ───────────────────────────────────────────────────


def test_assert_slo_passes_when_all_thresholds_met() -> None:
    result = assert_slo(
        p95_latency_seconds=300.0,  # 5 min < 8 min SLO
        success_rate=0.999,
        queue_depth_timeseries=[0, 5, 12, 8, 2, 0],
    )
    assert result.passed
    assert result.failures == []


def test_assert_slo_fails_on_latency_breach() -> None:
    result = assert_slo(
        p95_latency_seconds=500.0,  # > 8 min
        success_rate=0.999,
        queue_depth_timeseries=[0, 1, 0],
    )
    assert not result.passed
    assert any("p95 latency" in f for f in result.failures)


def test_assert_slo_fails_on_success_rate_breach() -> None:
    result = assert_slo(
        p95_latency_seconds=100.0,
        success_rate=0.98,  # < 99.5%
        queue_depth_timeseries=[0, 1, 0],
    )
    assert not result.passed
    assert any("success rate" in f for f in result.failures)


def test_assert_slo_fails_when_queue_does_not_drain() -> None:
    result = assert_slo(
        p95_latency_seconds=100.0,
        success_rate=0.999,
        queue_depth_timeseries=[0, 20, 50, 80, 95, 100],  # monotonically growing, never drains
    )
    assert not result.passed
    assert any("did not drain" in f for f in result.failures)


def test_assert_slo_fails_with_clear_breakdown_on_multiple_breaches() -> None:
    result = assert_slo(
        p95_latency_seconds=600.0, success_rate=0.5, queue_depth_timeseries=[10, 50, 60],
    )
    assert not result.passed
    assert len(result.failures) == 3
    rendered = result.render()
    assert "FAIL" in rendered


# ── Baseline regression comparison ────────────────────────────────────────


def _metrics(p95: float, success: float, tokens: float = 1000.0) -> BaselineMetrics:
    return BaselineMetrics(
        p50_latency_seconds=p95 * 0.6,
        p95_latency_seconds=p95,
        p99_latency_seconds=p95 * 1.2,
        success_rate=success,
        avg_tokens_per_run=tokens,
    )


def test_compare_to_baseline_flags_a_real_latency_regression() -> None:
    baseline = _metrics(p95=200.0, success=0.999)
    current = _metrics(p95=280.0, success=0.999)  # +40%, way over 10% tolerance

    regressions = compare_to_baseline(current, baseline)

    assert any("p95 latency regressed" in r for r in regressions)


def test_compare_to_baseline_flags_a_real_success_rate_regression() -> None:
    baseline = _metrics(p95=200.0, success=0.999)
    current = _metrics(p95=200.0, success=0.97)

    regressions = compare_to_baseline(current, baseline)

    assert any("success rate regressed" in r for r in regressions)


def test_compare_to_baseline_ignores_noise_within_tolerance() -> None:
    baseline = _metrics(p95=200.0, success=0.999, tokens=1000.0)
    current = _metrics(p95=205.0, success=0.998, tokens=1030.0)  # +2.5%, -0.1pp, +3%

    regressions = compare_to_baseline(current, baseline)

    assert regressions == []


def test_baseline_round_trips_through_disk(tmp_path: Path) -> None:
    metrics = _metrics(p95=250.0, success=0.996)

    assert load_baseline(tmp_path, "smoke") is None

    save_baseline(tmp_path, "smoke", metrics)
    loaded = load_baseline(tmp_path, "smoke")

    assert loaded == metrics
