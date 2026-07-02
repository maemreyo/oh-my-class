from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal, TypeVar

import anyio
from pydantic import BaseModel, ConfigDict, Field

from common.contracts.vocabulary_batch import InputNormalizationReport, NormalizedVocabularyCluster
from common.contracts.vocabulary_cluster_workflow import (
    VocabularyClusterStatus,
    VocabularyClusterWorkflow,
    apply_cluster_transition,
)
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


@dataclass(frozen=True, slots=True)
class VocabularyBatchStages:
    """The five per-cluster stages, injectable so the chain is testable without LLM.

    ``default_stages()`` wires the real capabilities; tests inject fakes. Keeping real
    defaults (not optional no-ops) is what keeps this orchestrator out of the
    false-green trap — the ``test_no_dark_runtime_modules`` lint guards it.
    """

    gather_evidence: Callable[..., Awaitable[Any]]
    ground: Callable[..., Awaitable[Any]]
    synthesize: Callable[..., Awaitable[Any]]
    make_practice: Callable[..., Awaitable[Any]]
    evaluate: Callable[..., Any]


def default_stages() -> VocabularyBatchStages:
    from packages.agents.sub_agents.content_creator.semantic_anchor_synthesis import (
        synthesize_semantic_anchor_cluster,
    )
    from packages.agents.sub_agents.practice_generator.semantic_anchor import (
        PracticeGenerationRequest,
        generate_semantic_anchor_practice,
    )
    from packages.agents.sub_agents.researcher.lexical_evidence import gather_cluster_evidence
    from packages.agents.sub_agents.researcher.lexical_grounding import lexical_grounding_profile
    from packages.quality.semantic_anchoring.gate import (
        SemanticAnchoringQualityGate,
        SemanticAnchoringQualityInput,
    )

    gate = SemanticAnchoringQualityGate()

    # Adapters keep the request/input Pydantic construction out of the orchestrator, so
    # the chain is decoupled and fakes need not rebuild these contracts in tests.
    async def make_practice(anchor: Any, run_id: str) -> Any:
        return await generate_semantic_anchor_practice(PracticeGenerationRequest(cluster=anchor), run_id)

    def evaluate(anchor: Any, practice: Any) -> Any:
        return gate.evaluate(SemanticAnchoringQualityInput(cluster=anchor, practice=practice))

    return VocabularyBatchStages(
        gather_evidence=gather_cluster_evidence,
        ground=lexical_grounding_profile,
        synthesize=synthesize_semantic_anchor_cluster,
        make_practice=make_practice,
        evaluate=evaluate,
    )


def _advance(
    workflow: VocabularyClusterWorkflow,
    target: VocabularyClusterStatus,
    *,
    error: str | None = None,
) -> VocabularyClusterWorkflow:
    new_status = apply_cluster_transition(workflow.status, target)
    updates: dict[str, object] = {"status": new_status}
    if error is not None:
        updates["last_error"] = error[:1000]
    return workflow.model_copy(update=updates)


@dataclass(frozen=True, slots=True)
class _ClusterOutcome:
    workflow: VocabularyClusterWorkflow
    content: dict[str, Any] | None  # produced anchor/practice, present only when passed


def _dump(obj: Any) -> Any:
    dump = getattr(obj, "model_dump", None)
    return dump(mode="json") if callable(dump) else obj


async def _process_cluster(
    cluster: NormalizedVocabularyCluster,
    snapshot_hash: str,
    run_id: str,
    stages: VocabularyBatchStages,
) -> _ClusterOutcome:
    """Run one cluster through ground -> synthesize -> practice -> gate, fail-closed.

    On a passing verdict the produced SemanticAnchorCluster + PracticeSet are captured
    as ``content`` so downstream render/export/review can consume them (not just status).
    """
    workflow = _workflow_from_cluster(run_id, cluster)
    try:
        workflow = _advance(workflow, "grounding")
        request = await stages.gather_evidence(cluster, snapshot_hash, run_id)
        bundle = await stages.ground(request, run_id)
        if bundle.readiness == "failed":
            return _ClusterOutcome(_advance(workflow, "failed", error="lexical grounding failed"), None)
        if bundle.readiness == "needs_review":
            return _ClusterOutcome(_advance(workflow, "needs_review"), None)

        workflow = _advance(workflow, "synthesizing")
        anchor = await stages.synthesize(cluster, bundle, run_id)

        workflow = _advance(workflow, "practice_generating")
        practice = await stages.make_practice(anchor, run_id)

        workflow = _advance(workflow, "validating")
        result = stages.evaluate(anchor, practice)
        final = _advance(workflow, result.verdict)
        content = None
        if final.status == "passed":
            content = {
                "cluster_id": cluster.cluster_id,
                "anchor": _dump(anchor),
                "practice": _dump(practice),
                "quality_verdict": getattr(result, "verdict", None),
            }
        return _ClusterOutcome(final, content)
    except Exception as exc:  # noqa: BLE001 - fail-closed: any stage error fails the cluster, never a silent pass
        return _ClusterOutcome(_advance(workflow, "failed", error=f"{type(exc).__name__}: {exc}"), None)


async def run_vocabulary_batch_orchestrator(
    state: dict[str, object],
    *,
    stages: VocabularyBatchStages | None = None,
    config: VocabularyBatchOrchestrationConfig | None = None,
) -> dict[str, object]:
    active_stages = stages or default_stages()
    active_config = config or VocabularyBatchOrchestrationConfig()
    report = InputNormalizationReport.model_validate(state.get("input_normalization_report") or {})
    run_id = str(state["run_id"])

    clusters_by_id = {cluster.cluster_id: cluster for cluster in report.ready_clusters}
    snapshot_hashes = {
        cluster.cluster_id: vocabulary_cluster_snapshot_hash(cluster.model_dump(mode="json"))
        for cluster in report.ready_clusters
    }

    async def worker(cluster_id: str) -> _ClusterOutcome:
        return await _process_cluster(
            clusters_by_id[cluster_id], snapshot_hashes[cluster_id], run_id, active_stages
        )

    outcomes = await process_clusters_with_concurrency(
        tuple(clusters_by_id), worker, active_config
    )
    workflows = [outcome.workflow for outcome in outcomes]
    cluster_content = [outcome.content for outcome in outcomes if outcome.content is not None]
    progress = _progress_from_workflows(workflows)
    return {
        "run_id": run_id,
        "vocabulary_cluster_workflows": [workflow.model_dump(mode="json") for workflow in workflows],
        "vocabulary_cluster_content": cluster_content,
        "vocabulary_batch_progress": progress.model_dump(mode="json"),
        "vocabulary_batch_events": [{
            "event": "vocabulary_batch_completed",
            "run_id": run_id,
            "total_clusters": progress.total_clusters,
            "status_counts": progress.status_counts,
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
