"""Unit tests for artifact_snapshot_service.

Tests the produce_artifact_snapshot() function with a fake renderer adapter,
proving that the production seam correctly calls renderer and persists snapshots.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.gateway.artifact_snapshot_service import produce_artifact_snapshot
from services.gateway.teaching_pack_snapshot_models import ArtifactSnapshot
from services.gateway.teaching_pack_types import RunId


@pytest.fixture
async def test_session() -> AsyncSession:
    """Create an in-memory test database session."""
    # For unit tests, we mock the session and store
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        from services.gateway.models import Base
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest.mark.asyncio
async def test_produce_artifact_snapshot_calls_renderer_and_persists():
    """Test that produce_artifact_snapshot calls renderer and creates snapshot."""
    run_id = RunId(f"test-run-{uuid4().hex[:8]}")
    artifact_content = {
        "title": "Test Lesson",
        "artifact_type": "lesson",
        "sections": [
            {"content": "Section 1", "teacher_only": False},
            {"content": "Answer Key", "teacher_only": True},
        ],
    }

    # Mock the render_artifact_content function
    mock_rendered_html = "<!DOCTYPE html><html><body><h1>Test Lesson</h1></body></html>"

    # Create a real session with mocked components
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.flush = AsyncMock()

    with patch(
        "services.gateway.artifact_snapshot_service.render_artifact_content",
        new_callable=AsyncMock,
        return_value=mock_rendered_html,
    ) as mock_render:
        with patch(
            "services.gateway.artifact_snapshot_service.TeachingPackSnapshotStore"
        ) as mock_store_class:
            # Setup mock snapshot store
            mock_store = MagicMock()
            mock_store.create_snapshot = AsyncMock()
            mock_store_class.return_value = mock_store

            # Setup mock snapshot result
            from services.gateway.teaching_pack_snapshot_store import ArtifactSnapshotRead
            mock_snapshot_result = ArtifactSnapshotRead(
                snapshot_id="test-snapshot-123",
                run_id=run_id,
                artifact_id="art-1",
                artifact_type="lesson",
                content_hash="abc123",
                html_hash="def456",
                content_json=artifact_content,
                rendered_html=mock_rendered_html,
                student_rendered_html="<!DOCTYPE html><html>student</html>",
                renderer_version="1.0",
                template_version="1.0",
                theme_version="1.0",
                standalone_valid=True,
                approved_at=None,
            )
            mock_store.create_snapshot.return_value = mock_snapshot_result

            # Call the production function
            snapshot_id = await produce_artifact_snapshot(
                mock_session,
                run_id=run_id,
                artifact_content=artifact_content,
                artifact_type="lesson",
            )

            # Assertions
            assert snapshot_id == "test-snapshot-123"
            mock_render.assert_called_once()
            call_args = mock_render.call_args
            assert call_args[0][0] == artifact_content
            mock_store.create_snapshot.assert_called_once()


@pytest.mark.asyncio
async def test_produce_artifact_snapshot_generates_artifact_id_if_not_provided():
    """Test that artifact_id is generated if not provided."""
    run_id = RunId(f"test-run-{uuid4().hex[:8]}")
    artifact_content = {"title": "Test"}

    mock_session = AsyncMock(spec=AsyncSession)
    mock_rendered_html = "<!DOCTYPE html><html></html>"

    with patch(
        "services.gateway.artifact_snapshot_service.render_artifact_content",
        new_callable=AsyncMock,
        return_value=mock_rendered_html,
    ):
        with patch(
            "services.gateway.artifact_snapshot_service.TeachingPackSnapshotStore"
        ) as mock_store_class:
            from services.gateway.teaching_pack_snapshot_store import ArtifactSnapshotRead
            
            mock_store = AsyncMock()
            mock_store_class.return_value = mock_store

            mock_snapshot_result = ArtifactSnapshotRead(
                snapshot_id="snap-1",
                run_id=run_id,
                artifact_id="artifact-abc12345",
                artifact_type="lesson",
                content_hash="xyz",
                html_hash="uvw",
                content_json=artifact_content,
                rendered_html=mock_rendered_html,
                student_rendered_html="<!DOCTYPE html>",
                renderer_version="1.0",
                template_version="1.0",
                theme_version="1.0",
                standalone_valid=True,
                approved_at=None,
            )
            mock_store.create_snapshot = AsyncMock(return_value=mock_snapshot_result)

            snapshot_id = await produce_artifact_snapshot(
                mock_session,
                run_id=run_id,
                artifact_content=artifact_content,
            )

            assert snapshot_id == "snap-1"
            # Verify that a snapshot was created with a generated artifact_id
            call_args = mock_store.create_snapshot.call_args
            assert call_args is not None
            snapshot_create_payload = call_args[0][0]
            assert snapshot_create_payload.artifact_id.startswith("artifact-")


@pytest.mark.asyncio
async def test_produce_artifact_snapshot_preserves_metadata():
    """Test that renderer and template versions are preserved in snapshot."""
    run_id = RunId(f"test-run-{uuid4().hex[:8]}")
    artifact_content = {"title": "Test"}

    mock_session = AsyncMock(spec=AsyncSession)
    mock_rendered_html = "<!DOCTYPE html><html></html>"

    with patch(
        "services.gateway.artifact_snapshot_service.render_artifact_content",
        new_callable=AsyncMock,
        return_value=mock_rendered_html,
    ):
        with patch(
            "services.gateway.artifact_snapshot_service.TeachingPackSnapshotStore"
        ) as mock_store_class:
            from services.gateway.teaching_pack_snapshot_store import ArtifactSnapshotRead
            
            mock_store = AsyncMock()
            mock_store_class.return_value = mock_store

            mock_snapshot_result = ArtifactSnapshotRead(
                snapshot_id="snap-1",
                run_id=run_id,
                artifact_id="art-1",
                artifact_type="quiz",
                content_hash="xyz",
                html_hash="uvw",
                content_json=artifact_content,
                rendered_html=mock_rendered_html,
                student_rendered_html="<!DOCTYPE html>",
                renderer_version="2.1",
                template_version="1.5",
                theme_version="ocean",
                standalone_valid=True,
                approved_at=None,
            )
            mock_store.create_snapshot = AsyncMock(return_value=mock_snapshot_result)

            await produce_artifact_snapshot(
                mock_session,
                run_id=run_id,
                artifact_content=artifact_content,
                artifact_type="quiz",
                renderer_version="2.1",
                template_version="1.5",
                theme_version="ocean",
            )

            # Verify metadata was passed to snapshot store
            call_args = mock_store.create_snapshot.call_args
            snapshot_create_payload = call_args[0][0]
            assert snapshot_create_payload.renderer_version == "2.1"
            assert snapshot_create_payload.template_version == "1.5"
            assert snapshot_create_payload.theme_version == "ocean"
            assert snapshot_create_payload.artifact_type == "quiz"


@pytest.mark.asyncio
async def test_produce_artifact_snapshot_renderer_error_propagates():
    """Test that renderer errors propagate to caller."""
    from services.gateway.renderer_adapter import RendererAdapterError
    
    run_id = RunId(f"test-run-{uuid4().hex[:8]}")
    artifact_content = {"title": "Test"}

    mock_session = AsyncMock(spec=AsyncSession)

    with patch(
        "services.gateway.artifact_snapshot_service.render_artifact_content",
        new_callable=AsyncMock,
        side_effect=RendererAdapterError("Renderer subprocess failed"),
    ):
        with pytest.raises(RendererAdapterError, match="Renderer subprocess failed"):
            await produce_artifact_snapshot(
                mock_session,
                run_id=run_id,
                artifact_content=artifact_content,
            )


@pytest.mark.asyncio
async def test_produce_artifact_snapshot_snapshot_store_error_propagates():
    """Test that snapshot store errors propagate to caller."""
    from services.gateway.teaching_pack_snapshot_store import SnapshotPersistenceError
    
    run_id = RunId(f"test-run-{uuid4().hex[:8]}")
    artifact_content = {"title": "Test"}

    mock_session = AsyncMock(spec=AsyncSession)
    mock_rendered_html = "<!DOCTYPE html><html></html>"

    with patch(
        "services.gateway.artifact_snapshot_service.render_artifact_content",
        new_callable=AsyncMock,
        return_value=mock_rendered_html,
    ):
        with patch(
            "services.gateway.artifact_snapshot_service.TeachingPackSnapshotStore"
        ) as mock_store_class:
            mock_store = MagicMock()
            mock_store.create_snapshot = AsyncMock(
                side_effect=SnapshotPersistenceError("snap-fail"),
            )
            mock_store_class.return_value = mock_store

            with pytest.raises(SnapshotPersistenceError):
                await produce_artifact_snapshot(
                    mock_session,
                    run_id=run_id,
                    artifact_content=artifact_content,
                )
