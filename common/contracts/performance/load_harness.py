"""Deterministic load/SLO report contracts for #130."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from typing import Iterable, Sequence


@dataclass(frozen=True)
class RunMeasurement:
    run_id: str
    latency_seconds: float
    succeeded: bool
    queue_depth_at_submit: int = 0
    queue_depth_at_finish: int = 0
    stage_latencies: tuple[tuple[str, float], ...] = ()
    breaker_trips: int = 0
    tokens_used: int = 0


@dataclass(frozen=True)
class LoadSLO:
    target_packs_per_day: int = 5000
    p95_latency_seconds_max: float = 480.0
    success_rate_min: float = 0.995
    queue_must_drain: bool = True
    max_regression_ratio: float = 0.10


@dataclass(frozen=True)
class LoadReport:
    profile: str
    sample_count: int
    throughput_per_day: float
    p50_latency_seconds: float
    p95_latency_seconds: float
    p99_latency_seconds: float
    success_rate: float
    initial_queue_depth: int
    final_queue_depth: int
    queue_drained: bool
    breaker_trips: int
    tokens_used: int
    passed: bool
    failures: tuple[str, ...]
    report_hash: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def percentile(values: Sequence[float], percentile_value: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    if not 0.0 <= percentile_value <= 1.0:
        raise ValueError("percentile must be between 0 and 1")
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    position = percentile_value * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def build_load_report(
    measurements: Iterable[RunMeasurement],
    *,
    profile: str,
    elapsed_seconds: float,
    slo: LoadSLO = LoadSLO(),
    baseline: LoadReport | None = None,
) -> LoadReport:
    samples = tuple(measurements)
    if not samples:
        raise ValueError("load report requires measurements")
    if elapsed_seconds <= 0:
        raise ValueError("elapsed_seconds must be positive")
    latencies = tuple(item.latency_seconds for item in samples)
    success_rate = sum(item.succeeded for item in samples) / len(samples)
    throughput = len(samples) * 86400.0 / elapsed_seconds
    initial_depth = max(item.queue_depth_at_submit for item in samples)
    final_depth = samples[-1].queue_depth_at_finish
    queue_drained = final_depth <= min(initial_depth, 1)
    p50 = percentile(latencies, 0.50)
    p95 = percentile(latencies, 0.95)
    p99 = percentile(latencies, 0.99)
    failures: list[str] = []
    if throughput < slo.target_packs_per_day:
        failures.append(f"throughput {throughput:.2f}/day below {slo.target_packs_per_day}/day")
    if p95 >= slo.p95_latency_seconds_max:
        failures.append(f"p95 {p95:.2f}s is not below {slo.p95_latency_seconds_max:.2f}s")
    if success_rate < slo.success_rate_min:
        failures.append(f"success rate {success_rate:.4f} below {slo.success_rate_min:.4f}")
    if slo.queue_must_drain and not queue_drained:
        failures.append(f"queue did not drain: {initial_depth} -> {final_depth}")
    if baseline is not None:
        if p95 > baseline.p95_latency_seconds * (1.0 + slo.max_regression_ratio):
            failures.append("p95 latency regressed beyond baseline tolerance")
        if success_rate + 1e-12 < baseline.success_rate:
            failures.append("success rate regressed below baseline")
    base = {
        "profile": profile,
        "sample_count": len(samples),
        "throughput_per_day": round(throughput, 4),
        "p50_latency_seconds": round(p50, 4),
        "p95_latency_seconds": round(p95, 4),
        "p99_latency_seconds": round(p99, 4),
        "success_rate": round(success_rate, 6),
        "initial_queue_depth": initial_depth,
        "final_queue_depth": final_depth,
        "queue_drained": queue_drained,
        "breaker_trips": sum(item.breaker_trips for item in samples),
        "tokens_used": sum(item.tokens_used for item in samples),
        "passed": not failures,
        "failures": tuple(failures),
    }
    report_hash = sha256(json.dumps(base, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return LoadReport(report_hash=report_hash, **base)
