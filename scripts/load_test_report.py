"""Perf report rendering for the QA-02 load harness — JSON (machine-readable,
diffable against a baseline) + a human-readable text summary suitable for a
release-gate readout."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from load_test_assert import SloAssertionResult
from load_test_metrics import PerfReport


@dataclass(frozen=True, slots=True)
class ReportPaths:
    json_path: Path
    text_path: Path


def build_report_json(
    *,
    profile_name: str,
    perf: PerfReport,
    assertion: SloAssertionResult,
    regressions: list[str],
    llm_mode: str,
    started_at: datetime,
    finished_at: datetime,
) -> dict[str, Any]:
    return {
        "schema": "oh-my-class.load_test.perf_report.v1",
        "profile": profile_name,
        "llm_mode": llm_mode,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "wall_clock_seconds": (finished_at - started_at).total_seconds(),
        "metrics": perf.to_json(),
        "slo_assertion": {"passed": assertion.passed, "failures": assertion.failures},
        "baseline_regressions": regressions,
    }


def render_text_summary(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        f"QA-02 load test report — profile={report['profile']} llm_mode={report['llm_mode']}",
        f"window: {report['started_at']} -> {report['finished_at']} "
        f"({report['wall_clock_seconds']:.1f}s wall clock)",
        "",
        f"submitted:  {metrics['total_submitted']}",
        f"terminal:   {metrics['total_terminal']}",
        f"completed:  {metrics['total_completed']}",
        f"success rate: {_fmt_pct(metrics['success_rate'])}",
        f"latency p50/p95/p99 (s): "
        f"{_fmt_num(metrics['p50_latency_seconds'])} / "
        f"{_fmt_num(metrics['p95_latency_seconds'])} / "
        f"{_fmt_num(metrics['p99_latency_seconds'])}",
        f"avg tokens/run: {_fmt_num(metrics['avg_tokens_per_run'])}",
        f"total cost (usd): {metrics['total_cost_usd']:.4f}",
        f"breaker trips: {metrics['breaker_trip_count']}",
        f"queue depth (start..end): "
        f"{_fmt_series(metrics['queue_depth_timeseries'])}",
        "",
        f"SLO assertion: {'PASS' if report['slo_assertion']['passed'] else 'FAIL'}",
    ]
    for failure in report["slo_assertion"]["failures"]:
        lines.append(f"  - {failure}")
    if report["baseline_regressions"]:
        lines.append("")
        lines.append("Baseline regressions:")
        for regression in report["baseline_regressions"]:
            lines.append(f"  - {regression}")
    else:
        lines.append("")
        lines.append("No baseline regressions flagged.")
    return "\n".join(lines) + "\n"


def write_report(output_dir: Path, report: dict[str, Any]) -> ReportPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "perf_report.json"
    text_path = output_dir / "perf_report.txt"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    text_path.write_text(render_text_summary(report), encoding="utf-8")
    return ReportPaths(json_path=json_path, text_path=text_path)


def _fmt_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def _fmt_num(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"


def _fmt_series(series: list[int]) -> str:
    if not series:
        return "n/a"
    if len(series) == 1:
        return str(series[0])
    return f"{series[0]}..{series[-1]} (peak {max(series)})"
