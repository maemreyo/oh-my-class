from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from common.contracts.vocabulary_cluster_workflow import VocabularyClusterEvidenceEntry, VocabularyClusterWorkflow
from services.gateway.vocabulary_cluster_models import (
    VocabularyClusterEvidenceModel,
    VocabularyClusterEvidenceType,
    VocabularyClusterReviewStatus,
    VocabularyClusterWorkflowModel,
    VocabularyClusterWorkflowStatus,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from services.gateway.teaching_pack_types import RunId


class VocabularyClusterWorkflowStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_workflow(self, state: VocabularyClusterWorkflow) -> None:
        statement = select(VocabularyClusterWorkflowModel).where(
            VocabularyClusterWorkflowModel.run_id == state.run_id,
            VocabularyClusterWorkflowModel.cluster_id == state.cluster_id,
        ).with_for_update()
        result = await self._session.execute(statement)
        workflow = result.scalar_one_or_none()
        if workflow is None:
            self._session.add(_workflow_model(state))
            await self._session.flush()
            return
        workflow.normalized_input = list(state.normalized_input)
        workflow.raw_input_span = state.raw_input_span
        workflow.status = VocabularyClusterWorkflowStatus(state.status)
        workflow.attempts = state.attempts
        workflow.review_status = VocabularyClusterReviewStatus(state.review_status)
        workflow.export_refs = state.export_refs
        workflow.snapshot_hash = state.snapshot_hash
        workflow.last_error = state.last_error
        await self._session.flush()

    async def get_workflow(self, run_id: RunId, cluster_id: str) -> VocabularyClusterWorkflow | None:
        statement = select(VocabularyClusterWorkflowModel).where(
            VocabularyClusterWorkflowModel.run_id == run_id,
            VocabularyClusterWorkflowModel.cluster_id == cluster_id,
        )
        result = await self._session.execute(statement)
        workflow = result.scalar_one_or_none()
        if workflow is None:
            return None
        return _workflow_contract(workflow)

    async def append_evidence(self, entry: VocabularyClusterEvidenceEntry) -> VocabularyClusterEvidenceEntry:
        self._session.add(VocabularyClusterEvidenceModel(
            evidence_id=entry.evidence_id,
            workflow_id=entry.workflow_id,
            cluster_id=entry.cluster_id,
            run_id=entry.run_id,
            sequence=entry.sequence,
            event_type=VocabularyClusterEvidenceType(entry.event_type),
            payload=entry.payload,
        ))
        await self._session.flush()
        return entry

    async def list_evidence(self, run_id: RunId, cluster_id: str) -> list[VocabularyClusterEvidenceEntry]:
        statement = (
            select(VocabularyClusterEvidenceModel)
            .where(
                VocabularyClusterEvidenceModel.run_id == run_id,
                VocabularyClusterEvidenceModel.cluster_id == cluster_id,
            )
            .order_by(VocabularyClusterEvidenceModel.sequence)
        )
        result = await self._session.execute(statement)
        return [_evidence_contract(entry) for entry in result.scalars().all()]


def _workflow_model(state: VocabularyClusterWorkflow) -> VocabularyClusterWorkflowModel:
    return VocabularyClusterWorkflowModel(
        workflow_id=state.workflow_id,
        cluster_id=state.cluster_id,
        run_id=state.run_id,
        normalized_input=list(state.normalized_input),
        raw_input_span=state.raw_input_span,
        status=VocabularyClusterWorkflowStatus(state.status),
        attempts=state.attempts,
        review_status=VocabularyClusterReviewStatus(state.review_status),
        export_refs=state.export_refs,
        snapshot_hash=state.snapshot_hash,
        last_error=state.last_error,
    )


def _workflow_contract(workflow: VocabularyClusterWorkflowModel) -> VocabularyClusterWorkflow:
    return VocabularyClusterWorkflow(
        workflow_id=workflow.workflow_id,
        cluster_id=workflow.cluster_id,
        run_id=workflow.run_id,
        normalized_input=tuple(workflow.normalized_input),
        raw_input_span=workflow.raw_input_span,
        status=workflow.status.value,
        attempts=workflow.attempts,
        review_status=workflow.review_status.value,
        export_refs=workflow.export_refs,
        snapshot_hash=workflow.snapshot_hash,
        last_error=workflow.last_error,
    )


def _evidence_contract(entry: VocabularyClusterEvidenceModel) -> VocabularyClusterEvidenceEntry:
    return VocabularyClusterEvidenceEntry(
        evidence_id=entry.evidence_id,
        workflow_id=entry.workflow_id,
        cluster_id=entry.cluster_id,
        run_id=entry.run_id,
        sequence=entry.sequence,
        event_type=entry.event_type.value,
        payload=entry.payload,
    )
