"""SLO assertion for the QA-02 load harness — ADR-034 north star:
p95 pack latency < 8 min, run-success >= 99.5%, queue drains (no unbounded growth).

Pure function over a metrics snapshot (scripts/load_test_metrics.py's PerfReport)
so it's testable with synthetic inputs, no DB/network needed.
"""
from __future__ import annotations

from dataclasses import dataclass

P95_LATENCY_SECONDS_MAX = 8 * 60
SUCCESS_RATE_MIN = 0.995
# Queue depth at the end of the run, as a fraction of the peak queue depth
# observed during the run — "drains" means it came back down, not that it
# hit exactly zero (a trailing in-flight job is fine).
QUEUE_DRAIN_RATIO_MAX = 0.1


@dataclass(frozen=True, slots=True)
class SloAssertionResult:
    passed: bool
    failures: list[str]

    def render(self) -> str:
        if self.passed:
            return "PASS — all SLOs met"
        return "FAIL — " + "; ".join(self.failures)


def assert_slo(
    *,
    p95_latency_seconds: float | None,
    success_rate: float | None,
    queue_depth_timeseries: list[int],
) -> SloAssertionResult:
    failures: list[str] = []

    if p95_latency_seconds is None:
        failures.append("p95 latency unavailable (no completed runs)")
    elif p95_latency_seconds >= P95_LATENCY_SECONDS_MAX:
        failures.append(
            f"p95 latency {p95_latency_seconds:.1f}s >= SLO max {P95_LATENCY_SECONDS_MAX}s"
        )

    if success_rate is None:
        failures.append("success rate unavailable (no terminal runs)")
    elif success_rate < SUCCESS_RATE_MIN:
        failures.append(f"success rate {success_rate:.4f} < SLO min {SUCCESS_RATE_MIN}")

    if not queue_depth_timeseries:
        failures.append("queue depth was never sampled")
    else:
        peak = max(queue_depth_timeseries)
        final = queue_depth_timeseries[-1]
        if peak > 0 and final / peak > QUEUE_DRAIN_RATIO_MAX:
            failures.append(
                f"queue did not drain: final depth {final} is "
                f"{final / peak:.0%} of peak {peak} (max allowed {QUEUE_DRAIN_RATIO_MAX:.0%})"
            )

    return SloAssertionResult(passed=not failures, failures=failures)
