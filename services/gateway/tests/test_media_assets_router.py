"""Integration tests for the media-assets router (SDX-02): upload, list/search,
and file retrieval, wired through a real Postgres session so the
teacher-scoping enforced by MediaAssetStore is exercised end-to-end over HTTP.

Tests are synchronous (not `async def`) and each opens its own async engine
inside a single `with TestClient(app) as client:` block. Starlette's
TestClient runs the ASGI app on its own private event loop (a "portal"); an
asyncpg connection created on one loop cannot be reused on another, so the
engine backing each client must never be touched outside that client's own
`with` block (a pytest-asyncio fixture's loop, or an ad hoc `asyncio.run`,
would each be a *different* loop and blow up with "attached to a different
loop"). Cleanup after each test opens a fresh, disposable engine of its own
under one throwaway `asyncio.run` for exactly the same reason.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi import FastAPI
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

if "jwt" not in sys.modules:
    sys.modules["jwt"] = MagicMock()

from services.gateway.auth.dependencies import require_teacher  # noqa: E402
from services.gateway.auth.models import Role, User  # noqa: E402
from services.gateway.middleware.error_handler import register_exception_handlers  # noqa: E402
from services.gateway.models import MediaAssetModel  # noqa: E402
from services.gateway.routers.media_assets import router  # noqa: E402
from services.gateway.teaching_pack_db import get_teaching_pack_session  # noqa: E402

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def _teacher(user_id: str) -> User:
    return User(user_id=user_id, username=user_id, role=Role.TEACHER)


def _build_app(user: User, tmp_path: Path) -> FastAPI:
    import os

    os.environ["MEDIA_STORAGE_ROOT"] = str(tmp_path)

    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session():
        async with session_factory() as session:
            yield session
            await session.commit()

    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)
    app.dependency_overrides[require_teacher] = lambda: user
    app.dependency_overrides[get_teaching_pack_session] = override_session
    return app


def _cleanup(asset_id: str) -> None:
    async def run() -> None:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        async with engine.connect() as connection:
            await connection.execute(delete(MediaAssetModel).where(MediaAssetModel.asset_id == asset_id))
            await connection.commit()
        await engine.dispose()

    asyncio.run(run())


class TestMediaAssetsRouter:
    def test_upload_then_list_then_fetch_file_round_trip(self, tmp_path: Path) -> None:
        teacher_id = f"teacher-{uuid4().hex[:8]}"
        app = _build_app(_teacher(teacher_id), tmp_path)

        with TestClient(app) as client:
            upload = client.post(
                "/media-assets",
                files={"file": ("frog-lifecycle.png", PNG_BYTES, "image/png")},
                data={"tags": "biology, diagram"},
            )
            assert upload.status_code == 200, upload.text
            created = upload.json()
            assert created["filename"] == "frog-lifecycle.png"
            assert created["tags"] == ["biology", "diagram"]
            assert created["alt_text"] is None
            assert created["storage_key"] == f"teacher-media/{teacher_id}/{created['asset_id']}.png"
            assert not created["storage_key"].startswith("runs/")

            listing = client.get("/media-assets", params={"q": "frog"})
            assert listing.status_code == 200
            assert [row["asset_id"] for row in listing.json()] == [created["asset_id"]]

            fetched_file = client.get(f"/media-assets/{created['asset_id']}/file")
            assert fetched_file.status_code == 200
            assert fetched_file.content == PNG_BYTES
            assert fetched_file.headers["content-type"] == "image/png"

        _cleanup(created["asset_id"])

    def test_rejects_non_image_uploads(self, tmp_path: Path) -> None:
        app = _build_app(_teacher(f"teacher-{uuid4().hex[:8]}"), tmp_path)

        with TestClient(app) as client:
            response = client.post(
                "/media-assets",
                files={"file": ("script.js", b"alert(1)", "application/javascript")},
            )

        assert response.status_code == 422

    def test_cross_teacher_isolation_over_http(self, tmp_path: Path) -> None:
        """Security-critical: a second teacher's client must not see or fetch
        the first teacher's uploaded asset through the HTTP surface."""
        owner_id = f"teacher-{uuid4().hex[:8]}"
        intruder_id = f"teacher-{uuid4().hex[:8]}"

        owner_app = _build_app(_teacher(owner_id), tmp_path)
        with TestClient(owner_app) as owner_client:
            upload = owner_client.post(
                "/media-assets",
                files={"file": ("private.png", PNG_BYTES, "image/png")},
            )
            asset_id = upload.json()["asset_id"]
            owner_fetch = owner_client.get(f"/media-assets/{asset_id}/file")
            assert owner_fetch.status_code == 200

        intruder_app = _build_app(_teacher(intruder_id), tmp_path)
        with TestClient(intruder_app) as intruder_client:
            intruder_list = intruder_client.get("/media-assets")
            intruder_fetch = intruder_client.get(f"/media-assets/{asset_id}/file")

        assert intruder_list.json() == []
        assert intruder_fetch.status_code == 404

        _cleanup(asset_id)
