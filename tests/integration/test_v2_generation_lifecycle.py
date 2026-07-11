from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from packages.agents.config.features import reset_features
from packages.agents.teaching_pack.graph import build_teaching_pack_graph
from packages.agents.teaching_pack.nodes import TeachingPackState
from packages.agents.teaching_pack.stages import StageEnum
from services.gateway.artifact_document_content_store import GatewayArtifactDocumentContentStore
from services.gateway.artifact_document_store import ArtifactDocumentStore
from services.gateway.models import Base
from services.gateway.teaching_pack_executor import TeachingPackResumeJob, TeachingPackStartJob
from services.gateway.teaching_pack_job_store import RunJobCreate, TeachingPackJobStore
from services.gateway.teaching_pack_models import RunJobKind
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId
from services.gateway.teaching_pack_worker import (
    TeachingPackJobExecutor,
    TeachingPackWorker,
    TeachingPackWorkerConfig,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession


DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture(autouse=True)
def _reset_feature_cache() -> Iterator[None]:
    """Guards this file's tests against feature-flag cache leakage: several
    of them enable `generic_content_creator_fallback_v1` via monkeypatch.setenv
    to force the fallback path (deliberately, to exercise the generic glue),
    which must not leak into other tests through the module-level singleton."""
    reset_features()
    yield
    reset_features()


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield factory
    await engine.dispose()


@pytest.mark.anyio
async def test_real_graph_persists_one_v2_quiz_document_and_answer_set(
    monkeypatch: pytest.MonkeyPatch,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = RunId(f"v2-graph-{uuid4()}")
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-v2-graph"),
            raw_request="Build a fractions quiz",
            class_info={"grade": 5},
        ))
        await session.commit()

    async def content_creator(_state: dict[str, object]) -> dict[str, object]:
        return {"artifacts": [{
            "artifact_id": "quiz-1",
            "artifact_type": "quiz",
            "theme": "default",
            "title": "Fractions quiz",
            "sections": [{"components": [{
                "type": "question_card",
                "id": "question-1",
                "text": "Which fraction equals one half?",
                "options": {"A": "1/4", "B": "2/4"},
                "answer": "B",
                "explain": "Two fourths equals one half.",
            }]}],
            "metadata": {},
            "accessibility": {"language": "en"},
        }]}

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        content_creator,
    )
    monkeypatch.setattr("packages.agents.teaching_pack.generate_one_artifact.get_specialist", lambda _artifact_type: None)
    monkeypatch.setenv("FEATURE_GENERIC_CONTENT_CREATOR_FALLBACK_V1", "true")
    reset_features()
    graph = build_teaching_pack_graph(
        content_store=GatewayArtifactDocumentContentStore(session_factory),
        interrupt_before=["render_quality"],
    )

    start_state: TeachingPackState = {
        "run_id": str(run_id),
        "contract": {"topic": "Fractions", "theme": "default"},
        "lesson_plan": {"topic": "Fractions"},
        "research_brief": {"sources": []},
        "artifact_types": ["quiz"],
        "completed_stages": [
            StageEnum.SETUP_CONTRACT,
            StageEnum.TRIAGE,
            StageEnum.PREPLANNING_SEARCH,
            StageEnum.PLANNING_BLUEPRINT,
            StageEnum.POST_BLUEPRINT_RESEARCH,
        ],
    }
    state = await graph.ainvoke(start_state)
    reference = state["artifact_references"][0]
    document_id = reference["document_id"]

    async with session_factory() as session:
        persisted = await ArtifactDocumentStore(session).get_persisted(document_id)

    assert persisted.document.document_id == document_id
    assert persisted.document.version == reference["version"]
    assert persisted.answer_set is not None
    assert persisted.answer_set.source_document_id == document_id
    assert "answer" not in persisted.document.model_dump(mode="json")


@pytest.mark.anyio
async def test_real_graph_persists_rich_lesson_components_without_loss(
    monkeypatch: pytest.MonkeyPatch,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = RunId(f"v2-rich-lesson-{uuid4()}")
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-v2-rich"),
            raw_request="Build a fractions lesson",
            class_info={"grade": 5},
        ))
        await session.commit()

    async def content_creator(_state: dict[str, object]) -> dict[str, object]:
        return {"artifacts": [{
            "artifact_id": "lesson-1",
            "artifact_type": "lesson",
            "theme": "ocean",
            "title": "Fractions lesson",
            "sections": [{"title": "Explore", "components": [
                {"type": "callout", "variant": "note", "title": "Remember", "body": "Equal parts have equal size."},
                {"type": "ordered_list", "items": ["Fold the strip.", "Compare the pieces."]},
            ]}],
            "metadata": {},
            "accessibility": {"language": "en"},
        }]}

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        content_creator,
    )
    monkeypatch.setattr("packages.agents.teaching_pack.generate_one_artifact.get_specialist", lambda _artifact_type: None)
    monkeypatch.setenv("FEATURE_GENERIC_CONTENT_CREATOR_FALLBACK_V1", "true")
    reset_features()
    graph = build_teaching_pack_graph(
        content_store=GatewayArtifactDocumentContentStore(session_factory),
        interrupt_before=["render_quality"],
    )
    start_state: TeachingPackState = {
        "run_id": str(run_id),
        "contract": {"topic": "Fractions", "theme": "ocean"},
        "lesson_plan": {"topic": "Fractions"},
        "research_brief": {"sources": []},
        "artifact_types": ["lesson"],
        "completed_stages": [
            StageEnum.SETUP_CONTRACT,
            StageEnum.TRIAGE,
            StageEnum.PREPLANNING_SEARCH,
            StageEnum.PLANNING_BLUEPRINT,
            StageEnum.POST_BLUEPRINT_RESEARCH,
        ],
    }

    state = await graph.ainvoke(start_state)
    document_id = state["artifact_references"][0]["document_id"]
    async with session_factory() as session:
        persisted = await ArtifactDocumentStore(session).get_persisted(document_id)

    assert persisted.document.payload.payload_kind == "rich_document"
    rich_sections = persisted.document.payload.rich_sections
    assert rich_sections is not None
    assert rich_sections[0].components[0]["type"] == "callout"
    assert persisted.answer_set is None


@pytest.mark.anyio
async def test_queued_worker_persists_v2_quiz_document_and_answer_set(
    monkeypatch: pytest.MonkeyPatch,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    run_id = RunId(f"v2-worker-{uuid4()}")
    start_state: TeachingPackState = {
        "run_id": str(run_id),
        "contract": {"topic": "Fractions", "theme": "default"},
        "lesson_plan": {"topic": "Fractions"},
        "research_brief": {"sources": []},
        "artifact_types": ["quiz"],
        "completed_stages": [
            StageEnum.SETUP_CONTRACT,
            StageEnum.TRIAGE,
            StageEnum.PREPLANNING_SEARCH,
            StageEnum.PLANNING_BLUEPRINT,
            StageEnum.POST_BLUEPRINT_RESEARCH,
        ],
    }
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-v2-worker"),
            raw_request="Build a fractions quiz",
            class_info={"grade": 5},
        ))
        await TeachingPackJobStore(session).enqueue(RunJobCreate(
            job_id=f"job-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.START,
            idempotency_key=f"v2-worker-{run_id}",
            payload={"initial_state": {
                "run_id": str(run_id),
                "contract": {"topic": "Fractions", "theme": "default"},
                "lesson_plan": {"topic": "Fractions"},
                "research_brief": {"sources": []},
                "artifact_types": ["quiz"],
                "completed_stages": [
                    "setup_contract", "triage", "preplanning_search", "planning_blueprint", "post_blueprint_research",
                ],
            }},
        ))
        await session.commit()

    async def content_creator(_state: dict[str, object]) -> dict[str, object]:
        return {"artifacts": [{
            "artifact_id": "quiz-1", "artifact_type": "quiz", "theme": "default", "title": "Fractions quiz",
            "sections": [{"components": [{
                "type": "question_card", "id": "question-1", "text": "Which fraction equals one half?",
                "options": {"A": "1/4", "B": "2/4"}, "answer": "B", "explain": "Two fourths equals one half.",
            }]}],
            "metadata": {}, "accessibility": {"language": "en"},
        }]}

    monkeypatch.setattr("packages.agents.teaching_pack.generate_one_artifact.content_creator_node", content_creator)
    monkeypatch.setattr("packages.agents.teaching_pack.generate_one_artifact.get_specialist", lambda _artifact_type: None)
    monkeypatch.setenv("FEATURE_GENERIC_CONTENT_CREATOR_FALLBACK_V1", "true")
    reset_features()
    graph = build_teaching_pack_graph(
        content_store=GatewayArtifactDocumentContentStore(session_factory),
        interrupt_before=["render_quality"],
    )

    class WorkerExecutor(TeachingPackJobExecutor):
        async def run_start_job(self, job: TeachingPackStartJob) -> None:
            assert job.initial_state["run_id"] == str(run_id)
            await graph.ainvoke(start_state)

        async def run_resume_job(self, job: TeachingPackResumeJob) -> None:
            _ = job
            raise AssertionError("queued test only schedules a start job")

    async with session_factory() as session:
        worker = TeachingPackWorker(
            TeachingPackJobStore(session),
            WorkerExecutor(),
            TeachingPackWorkerConfig(worker_id="v2-worker", lease_seconds=30, idle_sleep_seconds=0),
        )
        assert await worker.run_one() is True
        await session.commit()
    async with session_factory() as session:
        latest = await ArtifactDocumentStore(session).get_latest(run_id, "quiz-1")
        assert latest is not None
        persisted = await ArtifactDocumentStore(session).get_persisted(latest.document_id)

    assert persisted.answer_set is not None
    assert persisted.answer_set.entries[0].correct_option_ids == ["B"]
