"""Integration tests for snapshots router.

Tests the POST /run/{run_id}/snapshots endpoint with mocked dependencies,
proving the production caller flow works end-to-end.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from services.gateway.pipeline_v2_types import RunId, TeacherId


@pytest.mark.asyncio
async def test_produce_snapshot_endpoint_calls_service():
    """Test that the endpoint successfully calls produce_artifact_snapshot."""
    from services.gateway.routers.snapshots import produce_snapshot
    from services.gateway.auth.models import Role, User
    from unittest.mock import MagicMock
    from contextlib import asynccontextmanager

    run_id = RunId(f"run-{uuid4().hex[:8]}")
    teacher_id = TeacherId(f"teacher-{uuid4().hex[:8]}")
    
    mock_user = User(
        user_id=teacher_id,
        username="testteacher",
        role=Role.TEACHER,
    )

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()

    @asynccontextmanager
    async def mock_session_factory():
        yield mock_session

    mock_request = MagicMock()
    mock_request.app.state.runs = {
        run_id: {"teacher_id": teacher_id, "state": {}}
    }
    mock_request.app.state.pipeline_v2_session_factory = mock_session_factory

    request_body = {
        "artifact_content": {
            "title": "Test Lesson",
            "sections": [{"content": "Test section"}],
        },
        "artifact_type": "lesson",
        "renderer_version": "1.0",
    }

    with patch("services.gateway.routers.snapshots.produce_artifact_snapshot", new_callable=AsyncMock) as mock_produce:
        mock_produce.return_value = "snapshot-123"

        from services.gateway.routers.snapshots import ProduceSnapshotRequest
        result = await produce_snapshot(
            run_id,
            ProduceSnapshotRequest(**request_body),
            mock_request,
            mock_user,
        )

        assert result.snapshot_id == "snapshot-123"
        mock_produce.assert_called_once()


def test_authorization_rejects_unauthorized_teacher():
    """Test _require_owner rejects unauthorized teacher."""
    from services.gateway.routers.snapshots import _require_owner
    from services.gateway.auth.models import Role, User
    from services.gateway.exceptions import AuthorizationError

    teacher1_id = TeacherId(f"teacher-{uuid4().hex[:8]}")
    teacher2_id = TeacherId(f"teacher-{uuid4().hex[:8]}")
    
    run_data = {"teacher_id": teacher1_id}
    user = User(
        user_id=teacher2_id,
        username="other",
        role=Role.TEACHER,
    )

    with pytest.raises(AuthorizationError):
        _require_owner(run_data, user)


def test_authorization_allows_teacher_owner():
    """Test _require_owner allows the owner teacher."""
    from services.gateway.routers.snapshots import _require_owner
    from services.gateway.auth.models import Role, User

    teacher_id = TeacherId(f"teacher-{uuid4().hex[:8]}")
    run_data = {"teacher_id": teacher_id}
    user = User(
        user_id=teacher_id,
        username="owner",
        role=Role.TEACHER,
    )

    _require_owner(run_data, user)


def test_authorization_allows_admin():
    """Test _require_owner allows ADMIN regardless of owner."""
    from services.gateway.routers.snapshots import _require_owner
    from services.gateway.auth.models import Role, User

    teacher_id = TeacherId(f"teacher-{uuid4().hex[:8]}")
    admin_id = TeacherId(f"admin-{uuid4().hex[:8]}")
    
    run_data = {"teacher_id": teacher_id}
    user = User(
        user_id=admin_id,
        username="admin",
        role=Role.ADMIN,
    )

    _require_owner(run_data, user)
