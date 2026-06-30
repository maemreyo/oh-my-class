from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from services.gateway.models import (
    DecompositionFeedbackModel,
    DecompositionTemplateModel,
    TeacherPreferenceModel,
)
from services.gateway.teaching_pack_types import JsonObject, TeacherId


@dataclass(frozen=True, slots=True)
class DecompositionTemplateKey:
    teacher_id: TeacherId
    topic_normalized: str
    grade: str
    subject: str
    locale: str


class DecompositionMemoryStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def capture_feedback(
        self,
        key: DecompositionTemplateKey,
        proposed_sequence: JsonObject,
        approved_sequence: JsonObject,
        session_id: str | None,
    ) -> None:
        edit_types = _edit_types(proposed_sequence, approved_sequence)
        self._session.add(DecompositionFeedbackModel(
            feedback_id=f"feedback-{uuid4()}",
            teacher_id=key.teacher_id,
            session_id=session_id,
            proposed_sequence=proposed_sequence,
            approved_sequence=approved_sequence,
            edit_types=edit_types,
        ))
        await self._upsert_template(key, approved_sequence)
        await self._upsert_preferences(key.teacher_id, approved_sequence)
        await self._session.flush()

    async def get_template(self, key: DecompositionTemplateKey) -> JsonObject | None:
        result = await self._session.execute(select(DecompositionTemplateModel).where(
            DecompositionTemplateModel.teacher_id == key.teacher_id,
            DecompositionTemplateModel.topic_normalized == key.topic_normalized,
            DecompositionTemplateModel.grade == key.grade,
            DecompositionTemplateModel.subject == key.subject,
            DecompositionTemplateModel.locale == key.locale,
        ))
        row = result.scalar_one_or_none()
        return row.approved_sequence if row is not None else None

    async def get_preferences(self, teacher_id: TeacherId) -> JsonObject | None:
        result = await self._session.execute(select(TeacherPreferenceModel).where(
            TeacherPreferenceModel.teacher_id == teacher_id,
        ))
        row = result.scalar_one_or_none()
        return row.preferences if row is not None else None

    async def _upsert_template(self, key: DecompositionTemplateKey, approved_sequence: JsonObject) -> None:
        statement = pg_insert(DecompositionTemplateModel).values(
            template_id=f"template-{uuid4()}",
            teacher_id=key.teacher_id,
            topic_normalized=key.topic_normalized,
            grade=key.grade,
            subject=key.subject,
            locale=key.locale,
            approved_sequence=approved_sequence,
        ).on_conflict_do_update(
            constraint="uq_decomposition_template_key",
            set_={"approved_sequence": approved_sequence},
        )
        await self._session.execute(statement)

    async def _upsert_preferences(self, teacher_id: TeacherId, approved_sequence: JsonObject) -> None:
        preferences = {"preferred_session_duration_minutes": _average_duration(approved_sequence)}
        statement = pg_insert(TeacherPreferenceModel).values(
            teacher_id=teacher_id,
            preferences=preferences,
        ).on_conflict_do_update(
            constraint="uq_teacher_decomposition_preferences_teacher",
            set_={"preferences": preferences},
        )
        await self._session.execute(statement)


def _edit_types(proposed: JsonObject, approved: JsonObject) -> list[str]:
    edits: list[str] = []
    if len(_sessions(proposed)) != len(_sessions(approved)):
        edits.append("session_count")
    if _average_duration(proposed) != _average_duration(approved):
        edits.append("duration")
    return edits or ["content"]


def _average_duration(sequence: JsonObject) -> int:
    sessions = _sessions(sequence)
    durations = [session.get("duration_minutes") for session in sessions]
    values = [value for value in durations if isinstance(value, int)]
    if not values:
        return 45
    return round(sum(values) / len(values))


def _sessions(sequence: JsonObject) -> list[JsonObject]:
    value = sequence.get("sessions")
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
