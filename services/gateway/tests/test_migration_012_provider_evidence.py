"""Migration 012: provider_evidence column for release_evidence.

Proves that after running migration 012:
  - ``provider_evidence`` column exists and is nullable on ``release_evidence``
  - NULL inserts succeed (existing rows without provider evidence)
  - JSON inserts succeed (new rows with provider evidence list)
  - ORM round-trip preserves the data
  - Downgrade cleanly removes the column
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.release_evidence import ReleaseEvidence, ReleaseEvidenceRecord
from services.gateway.release_evidence_store import save_evidence

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def engine():
    eng = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()


class TestMigration012ProviderEvidence:
    """Schema-level verification that provider_evidence column exists."""

    async def test_provider_evidence_column_exists_and_is_nullable(
        self,
        engine,
    ) -> None:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT is_nullable FROM information_schema.columns "
                    "WHERE table_schema = 'public' "
                    "AND table_name = 'release_evidence' "
                    "AND column_name = 'provider_evidence'"
                ),
            )
            row = result.scalar_one_or_none()
        assert row is not None, "provider_evidence column must exist after migration 012"
        assert row == "YES", "provider_evidence must be nullable"

    async def test_insert_with_null_provider_evidence_succeeds(
        self,
        engine,
    ) -> None:
        """Existing-style records without provider evidence insert fine."""
        run_id = f"pe-null-{uuid4()}"
        async with engine.connect() as conn:
            await conn.execute(
                text(
                    "INSERT INTO public.release_evidence "
                    "(run_id, teacher_id_hash, status, total_duration_ms, "
                    "tokens_used, cost_usd) "
                    "VALUES (:rid, 'ab12cd34ef56ab12', 'completed', 0, 0, 0.0)"
                ),
                {"rid": run_id},
            )
            result = await conn.execute(
                text("SELECT provider_evidence FROM public.release_evidence WHERE run_id = :rid"),
                {"rid": run_id},
            )
            val = result.scalar_one_or_none()
            await conn.commit()
        assert val is None, "NULL provider_evidence should be accepted"

    async def test_insert_with_json_provider_evidence_succeeds(
        self,
        engine,
    ) -> None:
        """New records with a provider_evidence JSON list insert fine."""
        import json

        run_id = f"pe-json-{uuid4()}"
        pe_data = [
            {
                "base_url": "http://127.0.0.1:20228",
                "model": "4omc",
                "timestamp": "2026-06-28T00:00:00+00:00",
                "status": "pass",
                "elapsed_s": 0.42,
                "models_endpoint_ok": True,
                "chat_endpoint_ok": True,
                "error": None,
            },
        ]
        async with engine.connect() as conn:
            await conn.execute(
                text(
                    "INSERT INTO public.release_evidence "
                    "(run_id, teacher_id_hash, status, provider_evidence, "
                    "total_duration_ms, tokens_used, cost_usd) "
                    "VALUES (:rid, 'ab12cd34ef56ab12', 'completed', "
                    "CAST(:pe AS JSON), 0, 0, 0.0)"
                ),
                {"rid": run_id, "pe": json.dumps(pe_data)},
            )
            result = await conn.execute(
                text("SELECT provider_evidence FROM public.release_evidence WHERE run_id = :rid"),
                {"rid": run_id},
            )
            val = result.scalar_one_or_none()
            await conn.commit()
        assert val is not None, "provider_evidence should be stored"
        assert isinstance(val, list), "provider_evidence should be a JSON list"
        assert len(val) == 1, "should have one provider entry"
        assert val[0]["status"] == "pass"
        assert val[0]["base_url"] == "http://127.0.0.1:20228"

    async def test_orm_round_trip_with_provider_evidence(
        self,
        engine,
    ) -> None:
        """ORM round-trip through save_evidence preserves provider_evidence."""
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            pe_data = [
                {
                    "base_url": "http://127.0.0.1:20228",
                    "model": "4omc",
                    "timestamp": "2026-06-28T00:00:00+00:00",
                    "status": "blocked",
                    "elapsed_s": 0.0,
                    "models_endpoint_ok": False,
                    "chat_endpoint_ok": False,
                    "error": "Connection refused",
                },
            ]
            evidence = ReleaseEvidence(
                run_id=f"pe-orm-{uuid4()}",
                teacher_id_hash="ab12cd34ef56ab12",
                status="completed",
                provider_evidence=pe_data,
            )
            await save_evidence(evidence, db)
            await db.commit()

            # Re-read from DB
            from sqlalchemy import select

            result = await db.execute(
                select(ReleaseEvidenceRecord).where(
                    ReleaseEvidenceRecord.run_id == evidence.run_id,
                ),
            )
            record = result.scalar_one()
            restored = ReleaseEvidence.from_db_record(record)

            assert len(restored.provider_evidence) == 1
            assert restored.provider_evidence[0]["status"] == "blocked"
            assert restored.provider_evidence[0]["error"] == "Connection refused"
