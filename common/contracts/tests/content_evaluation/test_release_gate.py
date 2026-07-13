from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from common.contracts.content_evaluation.benchmark import BenchmarkScenario, build_benchmark_report
from common.contracts.content_evaluation.release_gate import (
    DEFAULT_AXES,
    MUTATION_DIMENSION,
    build_pairwise_covering_array,
    calibrate_teacher_panel,
    detect_mutation,
    regression_failures,
    sign_payload,
    uncovered_pairs,
    verify_signature,
)
from scripts.run_content_benchmark import _artifact


def _positive_values() -> dict[str, str]:
    return {
        "artifact_type": "lesson",
        "family": "lesson_design",
        "subject": "math",
        "grade_band": "grades_3_5",
        "language": "en",
        "curriculum_lane": "ccss",
    }


def test_covering_array_covers_every_declared_pair_deterministically() -> None:
    first = build_pairwise_covering_array()
    second = build_pairwise_covering_array()
    assert first == second
    assert uncovered_pairs(first) == ()
    for axis, values in DEFAULT_AXES.items():
        assert set(values) <= {scenario.as_dict()[axis] for scenario in first}


def test_all_required_mutation_controls_are_detected() -> None:
    fixtures = {
        "hallucination": {"metadata": {}, "sections": []},
        "ambiguity": {"text": "ambiguous_fixture: multiple defensible answers"},
        "answer_leakage": {"answer": "A"},
        "shallow_pedagogy": {"text": "Which statement best matches this learning objective?"},
        "bias": {"text": "biased_fixture"},
        "unsafe_context": {"text": "unsafe_fixture"},
        "fake_citation": {"metadata": {"source": "https://example.invalid/fake"}},
    }
    assert set(fixtures) == set(MUTATION_DIMENSION)
    assert all(detect_mutation(name, fixture) for name, fixture in fixtures.items())


def test_teacher_calibration_tracks_false_pass_and_inter_rater_agreement() -> None:
    result = calibrate_teacher_panel(
        (True, True, False, True),
        ((True, False, False, True), (True, False, False, True), (True, True, False, True)),
    )
    assert result.false_pass_rate == 0.5
    assert not result.passed
    assert result.inter_rater_agreement >= 0.7


def test_signed_report_rejects_tampering() -> None:
    payload = {"dataset_version": "v1", "release_allowed": True}
    envelope = sign_payload(payload, key="test-key")
    assert verify_signature(payload, envelope, key="test-key")
    assert not verify_signature({**payload, "release_allowed": False}, envelope, key="test-key")


def test_release_baseline_regression_is_explicit() -> None:
    assert regression_failures({"pedagogy": 0.70}, {"pedagogy": 0.80}) == (
        "pedagogy regressed from 0.8000 to 0.7000",
    )


def test_smoke_positive_fixture_passes_every_base_oracle() -> None:
    values = _positive_values()
    scenario = BenchmarkScenario(
        scenario_id="smoke-positive",
        artifact_type=values["artifact_type"],
        family=values["family"],
        subject=values["subject"],
        grade_band=values["grade_band"],
        language=values["language"],
        curriculum_lane=values["curriculum_lane"],
        expected_pass=True,
    )
    report = build_benchmark_report(
        ((scenario, _artifact(values)),),
        dataset_version="content-smoke-contract.v1",
        graph_version="content-intelligence-pinned",
    )
    failed = [
        f"{result.dimension}:{result.score}"
        for result in report.oracle_results
        if not result.passed
    ]
    assert report.release_allowed, failed


def test_benchmark_smoke_cli_exits_zero_and_records_release_allowed(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[4]
    output = tmp_path / "content-benchmark-smoke.json"
    process = subprocess.run(
        [
            sys.executable,
            "scripts/run_content_benchmark.py",
            "--profile",
            "smoke",
            "--output",
            str(output),
        ],
        cwd=root,
        text=True,
        capture_output=True,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["release_allowed"] is True
    assert not any(payload["release_blockers"].values())
