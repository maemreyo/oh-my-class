from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select

from common.contracts.artifact_workflow import ArtifactWorkflowState
from services.gateway.teaching_pack_contract_edits import EDITABLE_CONTRACT_FIELDS
from services.gateway.teaching_pack_models import (
    ArtifactCheckStatus,
    ArtifactWorkflow,
    ArtifactWorkflowStatus,
    ContractRevision,
    GateInterrupt,
    GateInterruptStatus,
    GateResponse,
    RunContract,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from services.gateway.teaching_pack_types import JsonObject, RunId, TeacherId

@dataclass(frozen=True, slots=True)
class GateInterruptCreate:
    gate_id: str
    run_id: RunId
    gate_name: str
    payload: JsonObject


@dataclass(frozen=True, slots=True)
class GateResponseCreate:
    response_id: str
    gate_id: str
    run_id: RunId
    teacher_id: TeacherId
    response_json: JsonObject


class StaleGateResponseError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ArtifactWorkflowCreate:
    workflow_id: str
    run_id: RunId
    artifact_id: str
    artifact_type: str
    contract_revision_id: int = 1
    research_guidance_id: str = "guidance-default"


@dataclass(frozen=True, slots=True)
class RunContractCreate:
    contract_id: str
    run_id: RunId
    teacher_id: TeacherId
    contract_json: JsonObject


@dataclass(frozen=True, slots=True)
class ContractRevisionCreate:
    contract_id: str
    run_id: RunId
    revision: int
    contract_json: JsonObject


class TeachingPackControlStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_contract(self, payload: RunContractCreate) -> None:
        contract = RunContract(
            contract_id=payload.contract_id,
            run_id=payload.run_id,
            teacher_id=payload.teacher_id,
            contract_json=payload.contract_json,
            current_revision=1,
        )
        self._session.add(contract)
        await self._session.flush()
        self._session.add(ContractRevision(
            contract_id=payload.contract_id,
            run_id=payload.run_id,
            revision=1,
            contract_json=payload.contract_json,
        ))
        await self._session.flush()

    async def revise_contract(self, payload: ContractRevisionCreate) -> None:
        statement = select(RunContract).where(
            RunContract.contract_id == payload.contract_id,
            RunContract.run_id == payload.run_id,
        ).with_for_update()
        result = await self._session.execute(statement)
        contract = result.scalar_one()
        contract.contract_json = payload.contract_json
        contract.current_revision = payload.revision
        self._session.add(ContractRevision(
            contract_id=payload.contract_id,
            run_id=payload.run_id,
            revision=payload.revision,
            contract_json=payload.contract_json,
        ))
        await self._session.flush()

    async def apply_contract_edits(self, run_id: RunId, edits: JsonObject) -> int:
        statement = select(RunContract).where(RunContract.run_id == run_id).with_for_update()
        result = await self._session.execute(statement)
        contract = result.scalar_one()
        next_revision = contract.current_revision + 1
        editable_edits = {
            key: value for key, value in edits.items()
            if key in EDITABLE_CONTRACT_FIELDS
        }
        revised_contract = {**contract.contract_json, **editable_edits}
        await self.revise_contract(ContractRevisionCreate(
            contract_id=contract.contract_id,
            run_id=run_id,
            revision=next_revision,
            contract_json=revised_contract,
        ))
        return next_revision

    async def get_contract_json(self, run_id: RunId) -> JsonObject:
        statement = select(RunContract.contract_json).where(RunContract.run_id == run_id)
        result = await self._session.execute(statement)
        return result.scalar_one()

    async def open_gate(self, payload: GateInterruptCreate) -> None:
        self._session.add(GateInterrupt(
            gate_id=payload.gate_id,
            run_id=payload.run_id,
            gate_name=payload.gate_name,
            status=GateInterruptStatus.ACTIVE,
            payload=payload.payload,
            expires_at=None,
        ))
        await self._session.flush()

    async def list_active_gates(self, run_id: RunId) -> list[GateInterrupt]:
        statement = (
            select(GateInterrupt)
            .where(
                GateInterrupt.run_id == run_id,
                GateInterrupt.status == GateInterruptStatus.ACTIVE,
            )
            .order_by(GateInterrupt.created_at)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def cancel_active_gates(self, run_id: RunId) -> int:
        gates = await self.list_active_gates(run_id)
        for gate in gates:
            gate.status = GateInterruptStatus.CANCELLED
        await self._session.flush()
        return len(gates)

    async def respond_to_gate(self, payload: GateResponseCreate) -> None:
        statement = select(GateInterrupt).where(
            GateInterrupt.gate_id == payload.gate_id,
            GateInterrupt.run_id == payload.run_id,
        )
        result = await self._session.execute(statement)
        gate = result.scalar_one()
        if gate.status is not GateInterruptStatus.ACTIVE:
            raise StaleGateResponseError(payload.gate_id)
        gate.status = GateInterruptStatus.RESPONDED
        self._session.add(GateResponse(
            response_id=payload.response_id,
            gate_id=payload.gate_id,
            run_id=payload.run_id,
            teacher_id=payload.teacher_id,
            response_json=payload.response_json,
        ))
        await self._session.flush()

    async def create_artifact_workflow(self, payload: ArtifactWorkflowCreate) -> None:
        self._session.add(ArtifactWorkflow(
            workflow_id=payload.workflow_id,
            run_id=payload.run_id,
            artifact_id=payload.artifact_id,
            artifact_type=payload.artifact_type,
            status=ArtifactWorkflowStatus.QUEUED,
            attempts=0,
            contract_revision_id=payload.contract_revision_id,
            research_guidance_id=payload.research_guidance_id,
            validation_status=ArtifactCheckStatus.PENDING,
            judge_status=ArtifactCheckStatus.PENDING,
            snapshot_refs=[],
            snapshot_id=None,
            last_error=None,
        ))
        await self._session.flush()

    async def upsert_artifact_workflow_state(self, state: ArtifactWorkflowState) -> None:
        statement = select(ArtifactWorkflow).where(
            ArtifactWorkflow.run_id == state.run_id,
            ArtifactWorkflow.artifact_id == state.artifact_id,
        ).with_for_update()
        result = await self._session.execute(statement)
        workflow = result.scalar_one_or_none()
        if workflow is None:
            workflow = ArtifactWorkflow(
                workflow_id=state.workflow_id,
                run_id=state.run_id,
                artifact_id=state.artifact_id,
                artifact_type=state.artifact_type,
                status=ArtifactWorkflowStatus(state.status),
                attempts=state.attempts,
                contract_revision_id=state.contract_revision_id,
                research_guidance_id=state.research_guidance_id,
                validation_status=ArtifactCheckStatus(state.validation_status),
                judge_status=ArtifactCheckStatus(state.judge_status),
                snapshot_refs=state.snapshot_refs,
                snapshot_id=state.snapshot_refs[-1] if state.snapshot_refs else None,
                last_error=state.last_error,
            )
            self._session.add(workflow)
            await self._session.flush()
            return
        workflow.status = ArtifactWorkflowStatus(state.status)
        workflow.attempts = state.attempts
        workflow.contract_revision_id = state.contract_revision_id
        workflow.research_guidance_id = state.research_guidance_id
        workflow.validation_status = ArtifactCheckStatus(state.validation_status)
        workflow.judge_status = ArtifactCheckStatus(state.judge_status)
        workflow.snapshot_refs = state.snapshot_refs
        workflow.snapshot_id = state.snapshot_refs[-1] if state.snapshot_refs else None
        workflow.last_error = state.last_error
        await self._session.flush()

    async def get_artifact_workflow_state(
        self,
        run_id: RunId,
        artifact_id: str,
    ) -> ArtifactWorkflowState | None:
        statement = select(ArtifactWorkflow).where(
            ArtifactWorkflow.run_id == run_id,
            ArtifactWorkflow.artifact_id == artifact_id,
        )
        result = await self._session.execute(statement)
        workflow = result.scalar_one_or_none()
        if workflow is None:
            return None
        return ArtifactWorkflowState.model_validate({
            "workflow_id": workflow.workflow_id,
            "run_id": workflow.run_id,
            "artifact_id": workflow.artifact_id,
            "artifact_type": workflow.artifact_type,
            "status": workflow.status.value,
            "attempts": workflow.attempts,
            "contract_revision_id": workflow.contract_revision_id,
            "research_guidance_id": workflow.research_guidance_id,
            "validation_status": workflow.validation_status.value,
            "judge_status": workflow.judge_status.value,
            "snapshot_refs": workflow.snapshot_refs,
            "last_error": workflow.last_error,
        })

    async def set_artifact_status(
        self,
        run_id: RunId,
        artifact_id: str,
        status: ArtifactWorkflowStatus,
    ) -> None:
        statement = select(ArtifactWorkflow).where(
            ArtifactWorkflow.run_id == run_id,
            ArtifactWorkflow.artifact_id == artifact_id,
        )
        result = await self._session.execute(statement)
        workflow = result.scalar_one()
        workflow.status = status
        await self._session.flush()
