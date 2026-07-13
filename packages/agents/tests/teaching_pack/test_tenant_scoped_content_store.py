from __future__ import annotations

import pytest

from common.contracts.artifact import ArtifactContent
from common.contracts.content_factory.tenancy import TenantAccessDeniedError, TenantContext
from packages.agents.teaching_pack.content_orchestrator import InMemoryArtifactContentStore
from packages.agents.teaching_pack.tenant_scoped_content_store import TenantScopedArtifactContentStore


def _tenant(organization_id: str) -> TenantContext:
    return TenantContext(
        organization_id=organization_id,
        principal_id=f"worker:{organization_id}",
        principal_role="worker",
    )


@pytest.mark.anyio
async def test_content_store_enforces_tenant_ownership_on_write_and_read() -> None:
    delegate = InMemoryArtifactContentStore()
    school_one = TenantScopedArtifactContentStore(delegate, _tenant("school-1"))
    reference = await school_one.persist(
        "run-1",
        "run-1:artifact:1",
        ArtifactContent(
            artifact_type="lesson",
            title="Tenant-safe lesson",
            sections=[{"title": "Lesson", "content": "Approved content"}],
            metadata={},
        ),
        "lesson-1",
    )

    projection = await school_one.read_projection(reference.document_id)
    assert projection.metadata["organization_id"] == "school-1"

    school_two = TenantScopedArtifactContentStore(delegate, _tenant("school-2"))
    with pytest.raises(TenantAccessDeniedError):
        await school_two.read_projection(reference.document_id)


@pytest.mark.anyio
async def test_content_store_fails_closed_for_unowned_legacy_document() -> None:
    delegate = InMemoryArtifactContentStore()
    reference = await delegate.persist(
        "run-legacy",
        "run-legacy:artifact:1",
        ArtifactContent(
            artifact_type="lesson",
            title="Legacy lesson",
            sections=[{"title": "Lesson", "content": "Legacy content"}],
            metadata={},
        ),
        "lesson-1",
    )

    guarded = TenantScopedArtifactContentStore(delegate, _tenant("school-1"))
    with pytest.raises(PermissionError, match="no organization ownership metadata"):
        await guarded.read_projection(reference.document_id)
