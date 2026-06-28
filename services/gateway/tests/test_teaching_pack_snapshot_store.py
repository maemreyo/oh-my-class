from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base, Run
from services.gateway.teaching_pack_snapshot_store import (
    AnswerKeyLeakageError,
    NonStandaloneSnapshotApprovalError,
    SnapshotPersistenceError,
    SnapshotVersionMismatchError,
    is_standalone_html,
    remove_answer_keys_from_html,
    snapshot_content_hash,
)
from services.gateway.teaching_pack_store import (
    ArtifactSnapshotCreate,
    TeachingPackRunCreate,
    TeachingPackRunStore,
)
from services.gateway.teaching_pack_types import RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


def test_snapshot_content_hash_uses_canonical_nested_json_order() -> None:
    first = {
        "title": "Fractions",
        "metadata": {"grade": 5, "subject": "math"},
        "sections": [{"body": "Compare", "title": "Warmup"}],
    }
    second = {
        "sections": [{"title": "Warmup", "body": "Compare"}],
        "metadata": {"subject": "math", "grade": 5},
        "title": "Fractions",
    }
    html = "<!DOCTYPE html><html><body>oh-my-class</body></html>"

    assert snapshot_content_hash(first, html) == snapshot_content_hash(second, html)


def test_standalone_html_allows_non_external_link_references() -> None:
    html = (
        '<!DOCTYPE html><html><head><link rel="preload" href="data:text/css,body{}">'
        '</head><body>oh-my-class</body></html>'
    )

    assert is_standalone_html(html)


def test_standalone_html_rejects_external_link_references() -> None:
    html = (
        '<!DOCTYPE html><html><head><link rel="stylesheet" '
        'href="https://cdn.example.com/style.css"></head><body>oh-my-class</body></html>'
    )

    assert not is_standalone_html(html)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(
            lambda sync_connection: set(Base.metadata.tables),
        )
        if "public.artifact_snapshots" not in existing_tables:
            pytest.skip("Teaching Pack snapshot tables are not present")
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()


async def test_duplicate_content_hash_does_not_return_other_run_snapshot(
    session: AsyncSession,
) -> None:
    first_run_id = RunId(f"test-{uuid4()}")
    second_run_id = RunId(f"test-{uuid4()}")
    store = TeachingPackRunStore(session)
    for run_id in (first_run_id, second_run_id):
        await store.create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-a"),
            raw_request="Teach clouds",
            class_info={"grade": 2},
        ))

    await store.create_snapshot(ArtifactSnapshotCreate(
        snapshot_id=f"snap-{uuid4()}",
        run_id=first_run_id,
        artifact_id="artifact-1",
        artifact_type="lesson",
        content_json={"title": "Clouds"},
        rendered_html="<!DOCTYPE html><html><body>oh-my-class</body></html>",
        renderer_version="test-renderer@1",
    ))

    with pytest.raises(SnapshotPersistenceError):
        await store.create_snapshot(ArtifactSnapshotCreate(
            snapshot_id=f"snap-{uuid4()}",
            run_id=second_run_id,
            artifact_id="artifact-1",
            artifact_type="lesson",
            content_json={"title": "Clouds"},
            rendered_html="<!DOCTYPE html><html><body>oh-my-class</body></html>",
            renderer_version="test-renderer@1",
        ))

    await session.execute(delete(Run).where(Run.run_id.in_([first_run_id, second_run_id])))
    await session.commit()


async def test_duplicate_content_hash_blocks_version_mismatch(
    session: AsyncSession,
) -> None:
    run_id = RunId(f"test-{uuid4()}")
    store = TeachingPackRunStore(session)
    await store.create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-a"),
        raw_request="Teach clouds",
        class_info={"grade": 2},
    ))

    content_json = {"title": "Clouds"}
    rendered_html = "<!DOCTYPE html><html><body>oh-my-class</body></html>"
    await store.create_snapshot(ArtifactSnapshotCreate(
        snapshot_id=f"snap-{uuid4()}",
        run_id=run_id,
        artifact_id="artifact-1",
        artifact_type="lesson",
        content_json=content_json,
        rendered_html=rendered_html,
        renderer_version="test-renderer@1",
    ))

    with pytest.raises(SnapshotVersionMismatchError):
        await store.create_snapshot(ArtifactSnapshotCreate(
            snapshot_id=f"snap-{uuid4()}",
            run_id=run_id,
            artifact_id="artifact-1",
            artifact_type="lesson",
            content_json=content_json,
            rendered_html=rendered_html,
            renderer_version="test-renderer@2",
        ))

    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()


async def test_answer_key_removal_strips_teacher_only_sections(
    session: AsyncSession,
) -> None:
    from services.gateway.teaching_pack_snapshot_store import TeachingPackSnapshotStore

    run_id = RunId(f"test-{uuid4()}")
    store = TeachingPackRunStore(session)
    await store.create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-a"),
        raw_request="Teach with answers",
        class_info={"grade": 5},
    ))

    snapshot_id = f"snap-{uuid4()}"
    student_html_input = (
        "<!DOCTYPE html><html><body>"
        "<section>Student Content</section>"
        "<section data-answer-key=\"true\">Answer Key Here</section>"
        "<section data-teacher-only=\"true\">Teacher Notes</section>"
        "</body></html>"
    )
    await TeachingPackSnapshotStore(session).create_snapshot(ArtifactSnapshotCreate(
        snapshot_id=snapshot_id,
        run_id=run_id,
        artifact_id="artifact-1",
        artifact_type="quiz",
        content_json={"title": "Quiz"},
        rendered_html="<!DOCTYPE html><html><body>test</body></html>",
        renderer_version="test-renderer@1",
        student_rendered_html=student_html_input,
    ))
    snapshot = await TeachingPackSnapshotStore(session).get_snapshot(run_id, snapshot_id)

    assert snapshot is not None
    assert "Answer Key Here" not in snapshot.student_rendered_html
    assert "Teacher Notes" not in snapshot.student_rendered_html
    assert "Student Content" in snapshot.student_rendered_html
    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()


async def test_answer_key_removal_sanitizes_answer_patterns(
    session: AsyncSession,
) -> None:
    from services.gateway.teaching_pack_snapshot_store import TeachingPackSnapshotStore

    run_id = RunId(f"test-{uuid4()}")
    store = TeachingPackRunStore(session)
    await store.create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-a"),
        raw_request="Teach with inline answers",
        class_info={"grade": 5},
    ))

    snapshot_id = f"snap-{uuid4()}"
    student_html_input = (
        "<!DOCTYPE html><html><body>"
        "<p>Question: What is 2+2?</p>"
        "<p>Correct Answer: 4</p>"
        "<p>Solution: Add the numbers</p>"
        "</body></html>"
    )
    await TeachingPackSnapshotStore(session).create_snapshot(ArtifactSnapshotCreate(
        snapshot_id=snapshot_id,
        run_id=run_id,
        artifact_id="artifact-1",
        artifact_type="quiz",
        content_json={"title": "Quiz"},
        rendered_html="<!DOCTYPE html><html><body>test</body></html>",
        renderer_version="test-renderer@1",
        student_rendered_html=student_html_input,
    ))
    snapshot = await TeachingPackSnapshotStore(session).get_snapshot(run_id, snapshot_id)

    assert snapshot is not None
    student_html_lower = snapshot.student_rendered_html.lower()
    assert "correct answer" not in student_html_lower
    assert "solution:" not in student_html_lower
    assert "what is 2+2" in student_html_lower

    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()


async def test_non_standalone_snapshot_blocks_approval(
    session: AsyncSession,
) -> None:
    from services.gateway.teaching_pack_snapshot_store import TeachingPackSnapshotStore

    run_id = RunId(f"test-{uuid4()}")
    store = TeachingPackRunStore(session)
    await store.create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-a"),
        raw_request="Teach with CDN",
        class_info={"grade": 5},
    ))

    snapshot_id = f"snap-{uuid4()}"
    non_standalone_html = (
        "<!DOCTYPE html><html><head>"
        '<link rel="stylesheet" href="https://cdn.example.com/style.css">'
        "</head><body>oh-my-class</body></html>"
    )
    await TeachingPackSnapshotStore(session).create_snapshot(ArtifactSnapshotCreate(
        snapshot_id=snapshot_id,
        run_id=run_id,
        artifact_id="artifact-1",
        artifact_type="quiz",
        content_json={"title": "Quiz"},
        rendered_html=non_standalone_html,
        renderer_version="test-renderer@1",
    ))
    snapshot = await TeachingPackSnapshotStore(session).get_snapshot(run_id, snapshot_id)

    assert snapshot is not None
    assert not snapshot.standalone_valid

    with pytest.raises(NonStandaloneSnapshotApprovalError):
        await TeachingPackSnapshotStore(session).approve_snapshots(
            run_id,
            [snapshot.snapshot_id],
        )

    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()


def test_answer_key_removal_function() -> None:
    html_with_keys = (
        "<!DOCTYPE html><html><body>"
        "<section>Student Question</section>"
        "<section data-answer-key=\"true\">The Answer</section>"
        "<p>Answer Key: 42</p>"
        "<p>Correct: Yes</p>"
        "<p>Solution: Use formula</p>"
        "</body></html>"
    )
    cleaned = remove_answer_keys_from_html(html_with_keys)

    assert "The Answer" not in cleaned
    assert "Answer Key:" not in cleaned
    assert "Correct:" not in cleaned
    assert "Solution:" not in cleaned
    assert "Student Question" in cleaned


async def test_snapshot_answer_keys_not_in_main_rendered_html(
    session: AsyncSession,
) -> None:
    """Regression test: INVARIANT-05 — answer keys must not leak into main persisted rendered_html.
    
    Verifies that if ContentCreator puts answer keys outside teacher_only markers,
    create_snapshot rejects the snapshot and raises AnswerKeyLeakageError.
    The persisted snapshot.rendered_html must not contain answer patterns in
    student-facing sections.
    """
    from services.gateway.teaching_pack_snapshot_store import TeachingPackSnapshotStore

    run_id = RunId(f"test-{uuid4()}")
    store = TeachingPackRunStore(session)
    await store.create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-a"),
        raw_request="Teach with leaked answers",
        class_info={"grade": 5},
    ))

    snapshot_id_leaked = f"snap-{uuid4()}"
    leaked_html = (
        "<!DOCTYPE html><html><body>"
        "<section>Student Question: What is 2+2?</section>"
        "<p>Answer: 4</p>"
        "<p>This is the correct answer for students to see.</p>"
        "</body></html>"
    )
    
    with pytest.raises(AnswerKeyLeakageError) as exc_info:
        await TeachingPackSnapshotStore(session).create_snapshot(ArtifactSnapshotCreate(
            snapshot_id=snapshot_id_leaked,
            run_id=run_id,
            artifact_id="artifact-1",
            artifact_type="quiz",
            content_json={"title": "Quiz"},
            rendered_html=leaked_html,
            renderer_version="test-renderer@1",
        ))
    
    assert "answer_key_patterns_found_outside_marked_sections" in str(exc_info.value)
    
    snapshot_id_safe = f"snap-{uuid4()}"
    safe_html = (
        "<!DOCTYPE html><html><body>"
        "<section>Student Question: What is 2+2?</section>"
        "<section data-teacher-only=\"true\"><p>Answer: 4</p></section>"
        "</body></html>"
    )
    
    safe_snapshot = await TeachingPackSnapshotStore(session).create_snapshot(ArtifactSnapshotCreate(
        snapshot_id=snapshot_id_safe,
        run_id=run_id,
        artifact_id="artifact-2",
        artifact_type="quiz",
        content_json={"title": "Quiz"},
        rendered_html=safe_html,
        renderer_version="test-renderer@1",
    ))
    
    assert safe_snapshot is not None
    assert safe_snapshot.snapshot_id == snapshot_id_safe
    
    retrieved_snapshot = await TeachingPackSnapshotStore(session).get_snapshot(
        run_id,
        snapshot_id_safe,
    )
    assert retrieved_snapshot is not None
    assert "Student Question" in retrieved_snapshot.rendered_html
    assert "Answer: 4" in retrieved_snapshot.rendered_html
    assert "Answer: 4" not in retrieved_snapshot.student_rendered_html
    
    await session.execute(delete(Run).where(Run.run_id == run_id))
    await session.commit()
