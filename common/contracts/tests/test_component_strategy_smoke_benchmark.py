from __future__ import annotations

from pathlib import Path

from common.contracts.component_strategy_smoke_benchmark import run_component_strategy_smoke_benchmark


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = PROJECT_ROOT / ".scratch" / "component-strategist" / "fixtures"


def test_component_strategy_smoke_benchmark_covers_index_and_selector() -> None:
    report = run_component_strategy_smoke_benchmark(
        fixture_paths=(FIXTURE_DIR / "cs08_vocabulary_language_request.json",),
        p95_latency_ms_threshold=1_000.0,
    )

    assert report.index_opened_read_only is True
    assert report.query_result_count >= 1
    assert report.selector_result_count == 1
    assert report.p95_latency_ms <= 1_000.0
    assert report.abnormal_fallback_count == 0
    assert report.abnormal_no_match_count == 0
