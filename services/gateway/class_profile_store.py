from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from common.contracts.class_profile import ClassProfile
from packages.quality.layer2_content.pii import scrub_pii
from services.gateway.models import ClassProfileModel, Run
from services.gateway.retention import RetentionConfig

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_RETENTION = RetentionConfig()


class ClassProfileStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_profile(
        self,
        *,
        class_profile_id: str,
        teacher_id: str,
        profile: ClassProfile,
    ) -> ClassProfile:
        scrubbed = _scrub_profile(profile)
        row = ClassProfileModel(
            class_profile_id=class_profile_id,
            teacher_id=teacher_id,
            profile_json=scrubbed.model_dump(mode="json"),
            schema_version=scrubbed.schema_version,
            retention_days=_RETENTION.class_profiles,
        )
        self._session.add(row)
        await self._session.flush()
        return scrubbed

    async def get_profile(self, class_profile_id: str, teacher_id: str) -> ClassProfile | None:
        statement = select(ClassProfileModel).where(
            ClassProfileModel.class_profile_id == class_profile_id,
            ClassProfileModel.teacher_id == teacher_id,
            ClassProfileModel.deleted_at.is_(None),
        )
        result = await self._session.execute(statement)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return ClassProfile.model_validate(row.profile_json)

    async def update_profile(
        self,
        *,
        class_profile_id: str,
        teacher_id: str,
        profile: ClassProfile,
    ) -> ClassProfile | None:
        statement = select(ClassProfileModel).where(
            ClassProfileModel.class_profile_id == class_profile_id,
            ClassProfileModel.teacher_id == teacher_id,
            ClassProfileModel.deleted_at.is_(None),
        ).with_for_update()
        result = await self._session.execute(statement)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        scrubbed = _scrub_profile(profile)
        row.profile_json = scrubbed.model_dump(mode="json")
        row.schema_version = scrubbed.schema_version
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        return scrubbed

    async def snapshot_for_unit(
        self,
        *,
        class_profile_id: str,
        teacher_id: str,
        parent_run_id: str,
    ) -> ClassProfile | None:
        profile = await self.get_profile(class_profile_id, teacher_id)
        if profile is None:
            return None
        statement = select(Run).where(
            Run.run_id == parent_run_id,
            Run.teacher_id == teacher_id,
        ).with_for_update()
        result = await self._session.execute(statement)
        run = result.scalar_one_or_none()
        if run is None:
            return None
        run.persona_snapshot = profile.model_dump(mode="json")
        await self._session.flush()
        return profile

    async def soft_delete_profile(self, class_profile_id: str, teacher_id: str) -> bool:
        statement = select(ClassProfileModel).where(
            ClassProfileModel.class_profile_id == class_profile_id,
            ClassProfileModel.teacher_id == teacher_id,
            ClassProfileModel.deleted_at.is_(None),
        ).with_for_update()
        result = await self._session.execute(statement)
        row = result.scalar_one_or_none()
        if row is None:
            return False
        row.deleted_at = datetime.now(UTC)
        await self._session.flush()
        return True


def _scrub_profile(profile: ClassProfile) -> ClassProfile:
    scrubbed = scrub_pii(profile).value
    return ClassProfile.model_validate(scrubbed)
