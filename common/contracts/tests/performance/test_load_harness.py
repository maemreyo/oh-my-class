from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from common.contracts.performance.load_harness import (
    LoadReport,
    LoadSLO,
    RunMeasurement,
    build_load_report,
    percentile,
)


def _samples(*, slow: bool = False, fail: bool = False, final_depth: int = 0):
    return tuple(
        RunMeasurement(
            run_id=f"run-{index}",
            latency_seconds=600.0 if slow else 10.0 + index,
            succeeded=not fail or index > 0,
            queue_depth_at_submit=20,
            queue_depth_at_finish=final_depth if index == 19 else 10,
        )
        for index in range(20)
    )


def test_percentile_interpolates_deterministically() -> None:
    assert percentile((1.0, 2.0, 3.0, 4.0), 0.5) == 2.5


def test_green_profile_asserts_all_slos() -> None:
    report = build_load_report(_samples(), profile="smoke", elapsed_seconds=60.0)
    assert report.passed
    assert report.queue_drained
    assert report.success_rate == 1.0


def test_red_profile_proves_slo_gate_fails() -> None:
    report = build_load_report(
        _samples(slow=True, fail=True, final_depth=25),
        profile="red-control",
        elapsed_seconds=600.0,
    )
    assert not report.passed
    assert any("p95" in failure for failure in report.failures)
    assert any("success rate" in failure for failure in report.failures)
    assert any("queue did not drain" in failure for failure in report.failures)


def test_baseline_regression_is_blocking() -> None:
    baseline = build_load_report(_samples(), profile="baseline", elapsed_seconds=60.0)
    current = tuple(
        RunMeasurement(
            run_id=item.run_id,
            latency_seconds=item.latency_seconds * 1.25,
            succeeded=item.succeeded,
            queue_depth_at_submit=item.queue_depth_at_submit,
            queue_depth_at_finish=item.queue_depth_at_finish,
        )
        for item in _samples()
    )
    report = build_load_report(current, profile="release", elapsed_seconds=60.0, baseline=baseline)
    assert not report.passed
    assert "p95 latency regressed beyond baseline tolerance" in report.failures


def test_load_cli_green_and_red_controls_use_exit_codes(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[4]
    smoke_output = tmp_path / "smoke.json"
    smoke = subprocess.run(
        [
            sys.executable,
            "scripts/run_content_factory_load_test.py",
            "--profile",
            "smoke",
            "--output",
            str(smoke_output),
        ],
        cwd=root,
        text=True,
        capture_output=True,
    )
    assert smoke.returncode == 0, smoke.stdout + smoke.stderr
    assert json.loads(smoke_output.read_text(encoding="utf-8"))["passed"] is True

    red_output = tmp_path / "red.json"
    red = subprocess.run(
        [
            sys.executable,
            "scripts/run_content_factory_load_test.py",
            "--profile",
            "red-control",
            "--output",
            str(red_output),
        ],
        cwd=root,
        text=True,
        capture_output=True,
    )
    assert red.returncode == 1, red.stdout + red.stderr
    assert json.loads(red_output.read_text(encoding="utf-8"))["passed"] is False
