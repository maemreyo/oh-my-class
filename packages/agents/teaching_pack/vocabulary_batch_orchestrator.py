from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal, TypeVar

import anyio
from pydantic import BaseModel, ConfigDict, Field

from common.contracts.vocabulary_batch import InputNormalizationReport, NormalizedVocabularyCluster
from common.contracts.vocabulary_cluster_workflow import VocabularyClusterWorkflow
from packages.agents.teaching_pack.vocabulary_snapshot import vocabulary_cluster_snapshot_hash

type VocabularyFailureKind = Literal[
    "parse_ambiguity",
    "source_insufficiency",
    "schema_invalidity",
    "leakage",
    "renderer_failure",
    "unsupported_export",
]
type VocabularyFailureAction = Literal[
    "teacher_review",
    "retry_then_fail",
    "fail_cluster",
    "skip_export",
]

ResultT = TypeVar("ResultT")


class VocabularyBatchOrchestrationConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_expensive_stage_concurrency: int = Field(default=2, ge=1, le=20)


class VocabularyBatchProgress(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_clusters: int = Field(ge=0)
    status_counts: dict[str, int]


@dataclass(frozen=True, slots=True)
class VocabularyBatchInitialization:
    workflows: tuple[VocabularyClusterWorkflow, ...]
    progress: VocabularyBatchProgress


def is_vocabulary_batch_mode(state: dict[str, object]) -> bool:
    contract = state.get("contract")
    match contract:
        case dict():
            return contract.get("mode") == "vocabulary_batch"
        case None:
            return False
        case _:
            return False


def initialize_vocabulary_batch_workflows(
    run_id: str,
    report: InputNormalizationReport,
) -> VocabularyBatchInitialization:
    workflows = tuple(_workflow_from_cluster(run_id, cluster) for cluster in report.ready_clusters)
    return VocabularyBatchInitialization(
        workflows=workflows,
        progress=_progress_from_workflows(workflows),
    )


async def process_clusters_with_concurrency(
    cluster_ids: tuple[str, ...],
    worker: Callable[[str], Awaitable[ResultT]],
    config: VocabularyBatchOrchestrationConfig,
) -> tuple[ResultT, ...]:
    limiter = anyio.CapacityLimiter(config.max_expensive_stage_concurrency)
    results: list[ResultT | None] = [None for _ in cluster_ids]

    async def run_one(index: int, cluster_id: str) -> None:
        async with limiter:
            results[index] = await worker(cluster_id)

    async with anyio.create_task_group() as task_group:
        for index, cluster_id in enumerate(cluster_ids):
            task_group.start_soon(run_one, index, cluster_id)

    return tuple(_unwrap_result(result) for result in results)


def vocabulary_failure_action(failure: VocabularyFailureKind | str) -> VocabularyFailureAction:
    match failure:
        case "parse_ambiguity" | "source_insufficiency":
            return "teacher_review"
        case "schema_invalidity" | "renderer_failure":
            return "retry_then_fail"
        case "leakage":
            return "fail_cluster"
        case "unsupported_export":
            return "skip_export"
        case _:
            return "fail_cluster"


def run_vocabulary_batch_orchestrator(state: dict[str, object]) -> dict[str, object]:
    report = InputNormalizationReport.model_validate(state.get("input_normalization_report") or {})
    run_id = str(state["run_id"])
    initialized = initialize_vocabulary_batch_workflows(run_id, report)
    return {
        "run_id": run_id,
        "vocabulary_cluster_workflows": [
            workflow.model_dump(mode="json") for workflow in initialized.workflows
        ],
        "vocabulary_batch_progress": initialized.progress.model_dump(mode="json"),
        "vocabulary_batch_events": [{
            "event": "vocabulary_batch_initialized",
            "run_id": run_id,
            "total_clusters": initialized.progress.total_clusters,
            "status_counts": initialized.progress.status_counts,
        }],
    }


def _workflow_from_cluster(run_id: str, cluster: NormalizedVocabularyCluster) -> VocabularyClusterWorkflow:
    snapshot_hash = vocabulary_cluster_snapshot_hash(cluster.model_dump(mode="json"))
    return VocabularyClusterWorkflow(
        workflow_id=f"vocab-{run_id}-{cluster.cluster_id}",
        cluster_id=cluster.cluster_id,
        run_id=run_id,
        normalized_input=cluster.terms,
        raw_input_span=cluster.raw_input_span,
        status="queued",
        attempts=0,
        review_status="pending",
        export_refs={},
        snapshot_hash=snapshot_hash,
        last_error=None,
    )


def _progress_from_workflows(
    workflows: tuple[VocabularyClusterWorkflow, ...],
) -> VocabularyBatchProgress:
    counts: dict[str, int] = {}
    for workflow in workflows:
        counts[workflow.status] = counts.get(workflow.status, 0) + 1
    return VocabularyBatchProgress(total_clusters=len(workflows), status_counts=counts)


def _unwrap_result(result: ResultT | None) -> ResultT:
    if result is None:
        msg = "cluster worker did not produce a result"
        raise RuntimeError(msg)
    return result
