from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


async def get_pipeline_v2_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = request.app.state.pipeline_v2_session_factory
    async with session_factory() as session:
        yield session


PipelineV2Session = Annotated[AsyncSession, Depends(get_pipeline_v2_session)]
