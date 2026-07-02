from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.forms_response_capture import (
    FormsAnswer,
    FormsAnswerGrade,
    FormsCaptureRequest,
    FormsQuestionMapping,
    FormsResponse,
    capture_forms_responses,
    pseudonymize_respondent,
)
from services.gateway.models import Base
from services.gateway.outcome_models import GuardianConsent, StudentAttemptRecord
from services.gateway.outcome_store import grant_consent

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    database_engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with database_engine.begin() as connection:
        existing_tables = await connection.run_sync(lambda sync_conn: set(Base.metadata.tables))
        if "public.student_attempts" not in existing_tables:
            pytest.skip("student_attempts table is not present")
    yield database_engine
    await database_engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()


async def test_pulled_forms_response_records_pseudonymized_attempt_when_consented(session: AsyncSession) -> None:
    teacher_id = f"teacher-{uuid4()}"
    class_id = f"class-{uuid4()}"
    respondent = "student@example.com"
    pseudonym = pseudonymize_respondent(teacher_id, class_id, respondent)
    await grant_consent(session, teacher_id, class_id, pseudonym)
    await session.commit()

    request = FormsCaptureRequest(
        teacher_id=teacher_id,
        class_id=class_id,
        delivery_id="delivery-1",
        form_id="form-1",
        question_map={"item_1": FormsQuestionMapping("q-1", ("KC-fractions",))},
        essay_scores={},
    )
    response = FormsResponse(
        response_id="response-1",
        respondent=respondent,
        create_time=datetime(2026, 7, 2, tzinfo=UTC),
        answers={"item_1": FormsAnswer("item_1", FormsAnswerGrade(score=1.0, correct=True))},
    )

    attempts = await capture_forms_responses(session, request, [response])
    await session.commit()

    assert len(attempts) == 1
    assert attempts[0].student_pseudonym == pseudonym
    assert respondent not in attempts[0].student_pseudonym
    stored = await session.execute(select(StudentAttemptRecord).where(StudentAttemptRecord.attempt_id == attempts[0].attempt_id))
    row = stored.scalar_one()
    assert row.kc_ids == ["KC-fractions"]
    assert row.correct is True

    await session.execute(delete(StudentAttemptRecord).where(StudentAttemptRecord.teacher_id == teacher_id))
    await session.execute(delete(GuardianConsent).where(GuardianConsent.teacher_id == teacher_id))
    await session.commit()


async def test_pulled_forms_response_is_refused_without_consent(session: AsyncSession) -> None:
    teacher_id = f"teacher-{uuid4()}"
    class_id = f"class-{uuid4()}"
    request = FormsCaptureRequest(
        teacher_id=teacher_id,
        class_id=class_id,
        delivery_id="delivery-1",
        form_id="form-1",
        question_map={"essay": FormsQuestionMapping("q-essay", ("KC-writing",))},
        essay_scores={"response-essay:essay": 0.75},
    )
    response = FormsResponse(
        response_id="response-essay",
        respondent="writer@example.com",
        create_time=datetime(2026, 7, 2, tzinfo=UTC),
        answers={"essay": FormsAnswer("essay", text="Explanation")},
    )

    attempts = await capture_forms_responses(session, request, [response])
    await session.commit()

    assert attempts == []
