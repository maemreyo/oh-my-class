from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

from services.gateway.models import RunStatus
from services.gateway.notifications import notify_contract_confirmation, notify_gate_required
from services.gateway.teaching_pack_control_store import (
    GateInterruptCreate,
    TeachingPackControlStore,
    RunContractCreate,
)
from services.gateway.teaching_pack_job_store import TeachingPackJobStore, RunJobCreate
from services.gateway.teaching_pack_models import TeachingPackEventVisibility, RunJobKind
from services.gateway.teaching_pack_store import (
    TeachingPackEventCreate,
    TeachingPackRunCreate,
    TeachingPackRunStore,
    TeachingPackStatusTransition,
)
from services.gateway.teaching_pack_types import JsonObject, RunId, TeacherId
from services.gateway.research_safety import minimize_class_info
from services.gateway.retention import retention_days_for_class_info
from services.gateway.run_contract_setup import (
    ContractSetupGate,
    ContractSetupInput,
    ContractSetupReady,
    resolve_contract_setup,
)

if TYPE_CHECKING:
    from datetime import datetime

    from common.contracts.run_contract import RunContract


@dataclass(frozen=True, slots=True)
class TeachingPackCreateRunResult:
    run_id: RunId
    job_id: str | None
    status: RunStatus
    queued: bool = False


async def create_teaching_pack_run_record(
    session,
    *,
    teacher_id: TeacherId,
    raw_request: str,
    class_info: JsonObject,
    request_hash: str,
    idempotency_key: str | None,
    eligible_at: datetime | None = None,
) -> TeachingPackCreateRunResult:
    run_id = RunId(str(uuid4()))
    minimized_class_info = minimize_class_info(class_info)
    run_store = TeachingPackRunStore(session)
    await run_store.create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=teacher_id,
        raw_request=raw_request,
        class_info=minimized_class_info,
        retention_days=retention_days_for_class_info(minimized_class_info),
    ))
    setup = resolve_contract_setup(ContractSetupInput(
        run_id=run_id,
        teacher_id=teacher_id,
        raw_request=raw_request,
        class_info=minimized_class_info,
    ))
    match setup:
        case ContractSetupReady(contract=contract):
            return await _create_ready_run(
                session, run_store, contract, request_hash, idempotency_key, eligible_at,
            )
        case ContractSetupGate(gate_name=gate_name, payload=gate_payload, contract=contract):
            return await _create_gated_run(
                run_store,
                session,
                run_id,
                gate_name,
                gate_payload,
                contract,
                request_hash,
                idempotency_key,
            )


async def _create_ready_run(
    session,
    run_store: TeachingPackRunStore,
    contract: RunContract,
    request_hash: str,
    idempotency_key: str | None,
    eligible_at: datetime | None = None,
) -> TeachingPackCreateRunResult:
    control_store = TeachingPackControlStore(session)
    job_store = TeachingPackJobStore(session)
    job_id = f"job-{uuid4()}"
    await control_store.create_contract(RunContractCreate(
        contract_id=contract.contract_id,
        run_id=RunId(contract.run_id),
        teacher_id=TeacherId(contract.teacher_id),
        contract_json=contract.model_dump(mode="json"),
    ))
    await run_store.write_event(TeachingPackEventCreate(
        run_id=RunId(contract.run_id),
        event_name="teaching_pack.run.accepted",
        visibility=TeachingPackEventVisibility.TEACHER,
        payload={"job_id": job_id},
    ))
    job = await job_store.enqueue(RunJobCreate(
        job_id=job_id,
        run_id=RunId(contract.run_id),
        kind=RunJobKind.START,
        idempotency_key=idempotency_key or f"start:{contract.run_id}",
        payload={
            "source": "http_create",
            "request_hash": request_hash,
            "contract": contract.model_dump(mode="json"),
        },
        eligible_at=eligible_at,
    ))
    return TeachingPackCreateRunResult(
        run_id=job.run_id,
        job_id=job.job_id,
        status=RunStatus.PENDING,
        queued=eligible_at is not None,
    )


async def _create_gated_run(
    run_store: TeachingPackRunStore,
    session,
    run_id: RunId,
    gate_name: str,
    gate_payload: JsonObject,
    contract: RunContract | None,
    request_hash: str,
    idempotency_key: str | None,
) -> TeachingPackCreateRunResult:
    control_store = TeachingPackControlStore(session)
    if contract is not None:
        await control_store.create_contract(RunContractCreate(
            contract_id=contract.contract_id,
            run_id=run_id,
            teacher_id=TeacherId(contract.teacher_id),
            contract_json=contract.model_dump(mode="json"),
        ))
    gate_id = f"gate-{uuid4()}"
    await control_store.open_gate(GateInterruptCreate(
        gate_id=gate_id,
        run_id=run_id,
        gate_name=gate_name,
        payload={"gate_id": gate_id, **gate_payload},
    ))
    await run_store.transition_status(TeachingPackStatusTransition(
        run_id=run_id,
        status=RunStatus.AWAITING_APPROVAL,
        stage="setup_contract",
        reason=gate_name,
    ))
    await run_store.write_event(TeachingPackEventCreate(
        run_id=run_id,
        event_name=f"teaching_pack.{gate_name}.opened",
        visibility=TeachingPackEventVisibility.TEACHER,
        payload={"gate_id": gate_id, "gate_name": gate_name},
    ))
    run = await run_store.get_run_by_id(run_id)
    if run is not None:
        if gate_name == "contract_confirmation":
            await notify_contract_confirmation(run_id, run.teacher_id, session)
        else:
            await notify_gate_required(run_id, run.teacher_id, gate_name, session)
    if idempotency_key is not None:
        job_store = TeachingPackJobStore(session)
        await job_store.enqueue(RunJobCreate(
            job_id=f"job-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.START,
            idempotency_key=idempotency_key,
            payload={
                "source": "http_create",
                "request_hash": request_hash,
                "blocked_by_gate": gate_name,
            },
        ))
        await job_store.cancel_run_jobs(run_id)
    return TeachingPackCreateRunResult(run_id=run_id, job_id=None, status=RunStatus.AWAITING_APPROVAL)
