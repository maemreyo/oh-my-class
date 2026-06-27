from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base, Run
from services.gateway.pipeline_v2_control_store import (
    ArtifactWorkflowCreate,
    ContractRevisionCreate,
    GateInterruptCreate,
    GateResponseCreate,
    PipelineV2ControlStore,
    RunContractCreate,
)
from services.gateway.pipeline_v2_models import (
    ArtifactWorkflow,
    ArtifactWorkflowStatus,
    ContractRevision,
    GateInterrupt,
    GateInterruptStatus,
    RunContract,
)
from services.gateway.pipeline_v2_store import PipelineV2RunCreate, PipelineV2RunStore
from services.gateway.pipeline_v2_types import RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(
            lambda sync_connection: set(Base.metadata.tables),
        )
        if "public.gate_interrupts" not in existing_tables:
            pytest.skip("Pipeline V2 control tables are not present")
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()


class TestPipelineV2ControlStore:
    async def test_persists_gate_response_and_workflow(self, session: AsyncSession) -> None:
        run_id = RunId(f"test-{uuid4()}")
        teacher_id = TeacherId("teacher-a")
        run_store = PipelineV2RunStore(session)
        control_store = PipelineV2ControlStore(session)
        await run_store.create_run(PipelineV2RunCreate(
            run_id=run_id,
            teacher_id=teacher_id,
            raw_request="Teach energy",
            class_info={"grade": 7},
        ))

        await control_store.create_contract(RunContractCreate(
            contract_id=f"contract-{uuid4()}",
            run_id=run_id,
            teacher_id=teacher_id,
            contract_json={"language": "en"},
        ))
        gate_id = f"gate-{uuid4()}"
        await control_store.open_gate(GateInterruptCreate(
            gate_id=gate_id,
            run_id=run_id,
            gate_name="blueprint_approval",
            payload={"title": "Energy"},
        ))
        await control_store.respond_to_gate(GateResponseCreate(
            response_id=f"response-{uuid4()}",
            gate_id=gate_id,
            run_id=run_id,
            teacher_id=teacher_id,
            response_json={"action": "approve"},
        ))
        await control_store.create_artifact_workflow(ArtifactWorkflowCreate(
            workflow_id=f"workflow-{uuid4()}",
            run_id=run_id,
            artifact_id="lesson-1",
            artifact_type="lesson",
        ))
        await control_store.set_artifact_status(
            run_id,
            "lesson-1",
            ArtifactWorkflowStatus.PASSED,
        )
        await session.commit()

        gate = await session.get(GateInterrupt, gate_id)
        workflow_result = await session.execute(
            select(ArtifactWorkflow).where(
                ArtifactWorkflow.run_id == run_id,
                ArtifactWorkflow.artifact_id == "lesson-1",
            ),
        )
        workflow = workflow_result.scalar_one()

        assert gate is not None
        assert gate.status is GateInterruptStatus.RESPONDED
        assert workflow.status is ArtifactWorkflowStatus.PASSED

        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()

    async def test_contract_revisions_are_append_only(self, session: AsyncSession) -> None:
        run_id = RunId(f"test-{uuid4()}")
        teacher_id = TeacherId("teacher-a")
        control_store = PipelineV2ControlStore(session)
        await PipelineV2RunStore(session).create_run(PipelineV2RunCreate(
            run_id=run_id,
            teacher_id=teacher_id,
            raw_request="Teach energy",
            class_info={"grade": 7},
        ))
        contract_id = f"contract-{uuid4()}"

        await control_store.create_contract(RunContractCreate(
            contract_id=contract_id,
            run_id=run_id,
            teacher_id=teacher_id,
            contract_json={"topic": "Energy", "revision_meta": {"revision": 1}},
        ))
        await control_store.revise_contract(ContractRevisionCreate(
            contract_id=contract_id,
            run_id=run_id,
            revision=2,
            contract_json={
                "topic": "Energy transfer",
                "revision_meta": {
                    "revision": 2,
                    "actor": "teacher",
                    "source": "teacher",
                    "reason": "contract_gate_edit",
                    "effective_stage": "setup_contract",
                },
            },
        ))
        await session.commit()

        contract = await session.get(RunContract, contract_id)
        revisions = await session.execute(
            select(ContractRevision.revision, ContractRevision.contract_json)
            .where(ContractRevision.contract_id == contract_id)
            .order_by(ContractRevision.revision),
        )

        assert contract is not None
        assert contract.current_revision == 2
        assert [revision for revision, _ in revisions.all()] == [1, 2]

        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()


def test_pipeline_v2_control_tables_are_registered_in_metadata() -> None:
    assert "public.run_contracts" in Base.metadata.tables
    assert "public.contract_revisions" in Base.metadata.tables
    assert "public.gate_interrupts" in Base.metadata.tables
    assert "public.gate_responses" in Base.metadata.tables
    assert "public.artifact_workflows" in Base.metadata.tables
