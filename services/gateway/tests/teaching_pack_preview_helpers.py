from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Run, RunStatus
from services.gateway.teaching_pack_models import RunEvent
from services.gateway.teaching_pack_snapshot_models import ArtifactSnapshot
from services.gateway.teaching_pack_snapshot_store import (
    ArtifactSnapshotCreate,
    TeachingPackSnapshotStore,
)
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import JsonObject, RunId, TeacherId
from services.gateway.tests.teaching_pack_preview_db import DATABASE_URL


async def create_run_with_snapshot(
    run_id: RunId,
    snapshot_id: str,
    status: RunStatus = RunStatus.AWAITING_APPROVAL,
    rendered_html: str | None = None,
) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(
            TeachingPackRunCreate(
                run_id=run_id,
                teacher_id=TeacherId("teacher-preview"),
                raw_request="Teach rendered preview",
                class_info={"grade": 5},
            )
        )
        run = await session.get(Run, run_id)
        if run is not None:
            run.status = status
        await TeachingPackSnapshotStore(session).create_snapshot(
            ArtifactSnapshotCreate(
                snapshot_id=snapshot_id,
                run_id=run_id,
                artifact_id="lesson-1",
                artifact_type="lesson",
                content_json={
                    "title": f"Fractions {snapshot_id}",
                    "sections": [
                        {
                            "heading": "Question",
                            "content": "Student question <img src=x onerror=alert(1)>",
                        },
                        {
                            "heading": "Answer Key",
                            "content": "Correct answer",
                            "teacher_only": True,
                        },
                    ],
                },
                rendered_html=rendered_html
                or (
                    "<!DOCTYPE html><html><body><header>oh-my-class</header>"
                    f"<h1>Fractions {snapshot_id}</h1>"
                    "<section>Student question &lt;img src=x onerror=alert(1)&gt;</section>"
                    '<section data-teacher-only="true">Answer Key Correct answer</section>'
                    "</body></html>"
                ),
                renderer_version="renderer@test",
                template_version="template@test",
                theme_version="theme@test",
            )
        )
        await session.commit()
    await engine.dispose()


async def approved_event_payload(run_id: RunId) -> JsonObject:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(
            select(RunEvent.payload).where(
                RunEvent.run_id == run_id,
                RunEvent.event_name == "teaching_pack.content.approved_snapshots",
            ),
        )
        payload = result.scalar_one()
    await engine.dispose()
    return payload


async def delete_run(run_id: RunId) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(delete(ArtifactSnapshot).where(ArtifactSnapshot.run_id == run_id))
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()
    await engine.dispose()
