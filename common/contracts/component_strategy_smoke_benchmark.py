from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from pathlib import Path

from common.contracts.component_strategy import ComponentStrategyMode, ComponentStrategyRequest
from common.contracts.component_strategy_knowledge import DEFAULT_KNOWLEDGE_SOURCE_PATH, KnowledgeQuery, open_knowledge_index
from common.contracts.component_strategy_selector import plan_component_strategy
from common.contracts.grade_band import StrategyKnowledgeGradeBand


@dataclass(frozen=True, slots=True)
class ComponentStrategySmokeBenchmarkReport:
    index_opened_read_only: bool
    query_result_count: int
    selector_result_count: int
    p95_latency_ms: float
    abnormal_fallback_count: int
    abnormal_no_match_count: int


def run_component_strategy_smoke_benchmark(
    *,
    fixture_paths: tuple[Path, ...],
    p95_latency_ms_threshold: float,
) -> ComponentStrategySmokeBenchmarkReport:
    index = open_knowledge_index(_default_knowledge_index_path(), DEFAULT_KNOWLEDGE_SOURCE_PATH)
    query_results = index.query_bindings(
        KnowledgeQuery(
            artifact_type="lesson",
            subject_tag="language",
            grade_band=StrategyKnowledgeGradeBand.GRADES_4_6,
            bloom_level="understand",
            gagne_event="present_content",
            strategy_family_id="vocabulary_language",
        )
    )
    latencies = tuple(_selector_latency_ms(path) for path in fixture_paths)
    p95 = _p95(latencies)
    planned_results = tuple(_planned_request(path) for path in fixture_paths)
    fallback_count = sum(1 for result in planned_results if result.plan is not None and result.plan.recommended.fallback_metadata is not None)
    no_match_count = sum(1 for result in planned_results if result.plan is None)
    if p95 > p95_latency_ms_threshold:
        no_match_count += 1
    return ComponentStrategySmokeBenchmarkReport(
        index_opened_read_only=index.runtime_policy.query_only,
        query_result_count=len(query_results),
        selector_result_count=len(planned_results),
        p95_latency_ms=p95,
        abnormal_fallback_count=fallback_count,
        abnormal_no_match_count=no_match_count,
    )


def _selector_latency_ms(path: Path) -> float:
    start = time.perf_counter()
    _planned_request(path)
    return (time.perf_counter() - start) * 1_000


def _planned_request(path: Path):
    request = ComponentStrategyRequest.model_validate_json(path.read_text())
    return plan_component_strategy(request.model_copy(update={"mode": ComponentStrategyMode.FINAL}))


def _p95(values: tuple[float, ...]) -> float:
    if len(values) < 2:
        return values[0] if values else 0.0
    return statistics.quantiles(values, n=20, method="inclusive")[18]


def _default_knowledge_index_path() -> Path:
    return DEFAULT_KNOWLEDGE_SOURCE_PATH.with_suffix(".sqlite")
