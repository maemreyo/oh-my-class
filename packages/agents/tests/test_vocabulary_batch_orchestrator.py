from __future__ import annotations

from dataclasses import dataclass

import anyio
import pytest

from common.contracts.vocabulary_batch import InputNormalizationReport, NormalizedVocabularyCluster


def _report() -> InputNormalizationReport:
    return InputNormalizationReport(
        report_id="norm-1",
        ready_clusters=(
            NormalizedVocabularyCluster(cluster_id="cluster-1", terms=("fare", "ticket"), raw_input_span="fare / ticket", confidence=0.9),
            NormalizedVocabularyCluster(cluster_id="cluster-2", terms=("fee", "fare"), raw_input_span="fee / fare", confidence=0.9),
            NormalizedVocabularyCluster(cluster_id="cluster-3", terms=("journey", "trip"), raw_input_span="journey / trip", confidence=0.9),
        ),
        ambiguous_clusters=(),
        parse_confidence=0.92,
    )


@dataclass(slots=True)
class ConcurrencyProbe:
    active: int = 0
    peak: int = 0


@pytest.mark.asyncio
async def test_concurrency_cap_is_respected_with_fake_worker() -> None:
    from packages.agents.teaching_pack.vocabulary_batch_orchestrator import (
        VocabularyBatchOrchestrationConfig,
        process_clusters_with_concurrency,
    )

    probe = ConcurrencyProbe()

    async def worker(cluster_id: str) -> str:
        probe.active += 1
        probe.peak = max(probe.peak, probe.active)
        await anyio.sleep(0)
        probe.active -= 1
        return f"done:{cluster_id}"

    results = await process_clusters_with_concurrency(
        ("cluster-1", "cluster-2", "cluster-3"),
        worker,
        VocabularyBatchOrchestrationConfig(max_expensive_stage_concurrency=2),
    )

    assert probe.peak == 2
    assert results == ("done:cluster-1", "done:cluster-2", "done:cluster-3")


def test_initial_workflows_include_progress_summary() -> None:
    from packages.agents.teaching_pack.vocabulary_batch_orchestrator import initialize_vocabulary_batch_workflows

    result = initialize_vocabulary_batch_workflows(run_id="run-vocab", report=_report())

    assert result.progress.total_clusters == 3
    assert result.progress.status_counts == {"queued": 3}
    assert [workflow.cluster_id for workflow in result.workflows] == ["cluster-1", "cluster-2", "cluster-3"]
