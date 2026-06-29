from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from common.contracts.run_contract import ContractRevisionMeta, RunContract
from services.gateway.models import Base, Run
from services.gateway.teaching_pack_control_store import TeachingPackControlStore
from services.gateway.teaching_pack_models import GateInterrupt, RunEvent
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId
from services.gateway.research_engine import plan_search
from services.gateway.research_gate import (
    SearchPlanGateOpened,
    SearchPlanGateSkipped,
    prepare_search_plan_gate,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        tables = await connection.run_sync(lambda _: set(Base.metadata.tables))
        if "public.gate_interrupts" not in tables:
            pytest.skip("Teaching Pack control tables are not present")
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()


class TestResearchGate:
    async def test_opens_search_plan_confirmation_gate_when_plan_requires_it(
        self,
        session: AsyncSession,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        await _create_run(session, run_id)

        result = await prepare_search_plan_gate(
            run_id=run_id,
            plan=plan_search(_contract(locale="vi-VN", curriculum=None)),
            control_store=TeachingPackControlStore(session),
            run_store=TeachingPackRunStore(session),
        )
        await session.commit()

        assert isinstance(result, SearchPlanGateOpened)
        gate = await session.get(GateInterrupt, result.gate_id)
        event = await _latest_event(session, run_id)

        assert gate is not None
        assert gate.gate_name == "search_plan_confirmation"
        assert event == "teaching_pack.search_plan_confirmation.opened"
        await _delete_run(session, run_id)

    async def test_skips_search_plan_gate_when_plan_is_safe(self, session: AsyncSession) -> None:
        run_id = RunId(f"test-{uuid4()}")
        await _create_run(session, run_id)

        result = await prepare_search_plan_gate(
            run_id=run_id,
            plan=plan_search(_contract()),
            control_store=TeachingPackControlStore(session),
            run_store=TeachingPackRunStore(session),
        )
        await session.commit()

        gate_result = await session.execute(
            select(GateInterrupt).where(GateInterrupt.run_id == run_id),
        )
        event = await _latest_event(session, run_id)

        assert result == SearchPlanGateSkipped(reason="not_required")
        assert gate_result.scalar_one_or_none() is None
        assert event == "teaching_pack.search_plan.skipped_confirmation"
        await _delete_run(session, run_id)


async def _create_run(session: AsyncSession, run_id: RunId) -> None:
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-research"),
        raw_request="Teach fractions",
        class_info={"grade": 5, "subject": "math"},
    ))


async def _latest_event(session: AsyncSession, run_id: RunId) -> str:
    result = await session.execute(
        select(RunEvent.event_name)
        .where(RunEvent.run_id == run_id)
        .order_by(RunEvent.sequence.desc()),
    )
    return result.scalar_one()


async def _delete_run(session: AsyncSession, run_id: RunId) -> None:
    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()


def _contract(*, locale: str = "en-US", curriculum: str | None = "Common Core") -> RunContract:
    return RunContract(
        contract_id="contract-test",
        run_id="run-test",
        teacher_id="teacher-test",
        topic="Fractions",
        grade_band="Grade 5",
        subject="math",
        locale=locale,
        instruction_language="en",
        curriculum=curriculum,
        citation_locale=locale,
        artifact_types=["lesson"],
        export_formats=["html"],
        research_policy="standard",
        config_version="test",
        config_hash="0" * 64,
        revision_meta=ContractRevisionMeta(
            revision=1,
            actor="system",
            source="request",
            reason="test",
            effective_stage="setup_contract",
        ),
    )
