from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.exceptions import ErrorCode, OMCError
from services.gateway.models import Base
from services.gateway.teaching_session import service
from services.gateway.teaching_session.delivery_mode import (
    DELIVERY_MODE_POLICIES,
    IMPLEMENTED_DELIVERY_MODES,
)
from services.gateway.teaching_session.models import DeliveryMode, TeachingSession

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


class TestDeliveryModeEnum:
    """AC (amendment): delivery_mode is declared for all five modes now, defaults to live."""

    def test_all_five_modes_declared(self) -> None:
        assert {mode.value for mode in DeliveryMode} == {
            "live", "homework", "review", "flipped", "catch_up",
        }

    def test_delivery_mode_can_be_set_explicitly(self) -> None:
        # The column default only applies at flush/insert time (SQLAlchemy),
        # not on bare construction -- `TestCreateSessionDeliveryModeGate`
        # below covers the actual DB-level default via `service.create_session`.
        session = TeachingSession(
            session_id="s1", teacher_id="t1", deck_id="d1", snapshot_id="snap1",
            delivery_mode=DeliveryMode.LIVE,
        )
        assert session.delivery_mode == DeliveryMode.LIVE


class TestDeliveryModePolicyTable:
    """AC: each mode defines default response, retention, and sync behavior."""

    def test_all_five_modes_have_a_policy_entry(self) -> None:
        assert set(DELIVERY_MODE_POLICIES) == set(DeliveryMode)

    def test_every_policy_declares_the_three_required_fields(self) -> None:
        for policy in DELIVERY_MODE_POLICIES.values():
            assert policy.response_policy
            assert policy.retention_policy
            assert policy.sync_policy

    def test_only_live_is_teacher_controlled(self) -> None:
        for mode, policy in DELIVERY_MODE_POLICIES.items():
            assert policy.teacher_controlled == (mode is DeliveryMode.LIVE)

    def test_only_live_is_implemented(self) -> None:
        assert frozenset({DeliveryMode.LIVE}) == IMPLEMENTED_DELIVERY_MODES


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    database_engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with database_engine.begin() as connection:
        existing_tables = await connection.run_sync(
            lambda sync_connection: set(Base.metadata.tables),
        )
        if "public.teaching_sessions" not in existing_tables:
            pytest.skip("teaching_sessions table is not present — run alembic upgrade head")
    yield database_engine
    await database_engine.dispose()


@pytest.fixture
async def db(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()


class TestCreateSessionDeliveryModeGate:
    """AC (amendment): only `live` can be created; every other mode fails closed."""

    async def test_default_create_session_is_live(self, db: AsyncSession) -> None:
        created = await service.create_session(
            db,
            session_id=f"session-{uuid4()}",
            teacher_id=f"teacher-{uuid4()}",
            deck_id="deck-1",
            snapshot_id="snap-1",
        )
        await db.commit()

        assert created.delivery_mode == DeliveryMode.LIVE

    @pytest.mark.parametrize(
        "mode",
        [DeliveryMode.HOMEWORK, DeliveryMode.REVIEW, DeliveryMode.FLIPPED, DeliveryMode.CATCH_UP],
    )
    async def test_non_live_delivery_mode_is_rejected(
        self, db: AsyncSession, mode: DeliveryMode,
    ) -> None:
        with pytest.raises(OMCError) as excinfo:
            await service.create_session(
                db,
                session_id=f"session-{uuid4()}",
                teacher_id=f"teacher-{uuid4()}",
                deck_id="deck-1",
                snapshot_id="snap-1",
                delivery_mode=mode,
            )
        assert excinfo.value.error_code == ErrorCode.VALIDATION_ERROR
        assert excinfo.value.details[0]["field"] == "delivery_mode"
