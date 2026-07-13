"""Baseline storage + regression comparison for the QA-02 load harness.

Stores one JSON file per profile (smoke/full) under a baseline dir, and
flags a regression when the current perf report is meaningfully worse than
the stored baseline — "meaningfully" per an explicit tolerance so normal
run-to-run noise doesn't cry wolf.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Regressions must exceed these tolerances to be flagged — small deltas are
# noise. Latency/tokens: percent worse. Success: absolute percentage points
# worse (a rate near 1.0 makes percent-based comparison too sensitive).
LATENCY_TOLERANCE_PCT = 0.10
SUCCESS_RATE_TOLERANCE_PP = 0.005
TOKENS_TOLERANCE_PCT = 0.10


@dataclass(frozen=True, slots=True)
class BaselineMetrics:
    p50_latency_seconds: float | None
    p95_latency_seconds: float | None
    p99_latency_seconds: float | None
    success_rate: float | None
    avg_tokens_per_run: float | None

    def to_json(self) -> dict[str, Any]:
        return {
            "p50_latency_seconds": self.p50_latency_seconds,
            "p95_latency_seconds": self.p95_latency_seconds,
            "p99_latency_seconds": self.p99_latency_seconds,
            "success_rate": self.success_rate,
            "avg_tokens_per_run": self.avg_tokens_per_run,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> BaselineMetrics:
        return cls(
            p50_latency_seconds=data.get("p50_latency_seconds"),
            p95_latency_seconds=data.get("p95_latency_seconds"),
            p99_latency_seconds=data.get("p99_latency_seconds"),
            success_rate=data.get("success_rate"),
            avg_tokens_per_run=data.get("avg_tokens_per_run"),
        )


def baseline_path(baseline_dir: Path, profile_name: str) -> Path:
    return baseline_dir / f"{profile_name}.json"


def load_baseline(baseline_dir: Path, profile_name: str) -> BaselineMetrics | None:
    path = baseline_path(baseline_dir, profile_name)
    if not path.exists():
        return None
    return BaselineMetrics.from_json(json.loads(path.read_text(encoding="utf-8")))


def save_baseline(baseline_dir: Path, profile_name: str, metrics: BaselineMetrics) -> Path:
    baseline_dir.mkdir(parents=True, exist_ok=True)
    path = baseline_path(baseline_dir, profile_name)
    path.write_text(json.dumps(metrics.to_json(), indent=2) + "\n", encoding="utf-8")
    return path


def compare_to_baseline(current: BaselineMetrics, baseline: BaselineMetrics) -> list[str]:
    """Return a list of human-readable regression descriptions. Empty == no regression."""
    regressions: list[str] = []

    for label, attr in (
        ("p50 latency", "p50_latency_seconds"),
        ("p95 latency", "p95_latency_seconds"),
        ("p99 latency", "p99_latency_seconds"),
        ("avg tokens/run", "avg_tokens_per_run"),
    ):
        cur = getattr(current, attr)
        base = getattr(baseline, attr)
        if cur is None or base is None or base <= 0:
            continue
        pct_change = (cur - base) / base
        tolerance = TOKENS_TOLERANCE_PCT if attr == "avg_tokens_per_run" else LATENCY_TOLERANCE_PCT
        if pct_change > tolerance:
            regressions.append(
                f"{label} regressed: {cur:.2f} vs baseline {base:.2f} "
                f"(+{pct_change:.1%}, tolerance {tolerance:.0%})"
            )

    if current.success_rate is not None and baseline.success_rate is not None:
        delta = baseline.success_rate - current.success_rate
        if delta > SUCCESS_RATE_TOLERANCE_PP:
            regressions.append(
                f"success rate regressed: {current.success_rate:.4f} vs baseline "
                f"{baseline.success_rate:.4f} (-{delta:.4f}, tolerance {SUCCESS_RATE_TOLERANCE_PP})"
            )

    return regressions
