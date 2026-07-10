from __future__ import annotations

import pytest

from common.contracts.artifact import ArtifactContent
from packages.agents.teaching_pack.content_orchestrator import (
    ArtifactDocumentReference,
    InMemoryArtifactContentStore,
)
from packages.agents.teaching_pack.reducers import current_generation_artifact_references


def _artifact() -> ArtifactContent:
    return ArtifactContent(
        artifact_id="lesson-1",
        artifact_type="lesson",
        theme="default",
        title="Fractions lesson",
        sections=[{"title": "Introduction", "content": "A fraction names equal parts."}],
        metadata={},
        accessibility={"language": "en"},
    )


@pytest.mark.anyio
async def test_content_store_returns_reference_without_payload() -> None:
    store = InMemoryArtifactContentStore()

    reference = await store.persist("run-1", "run-1:artifact:1", _artifact(), "lesson-1")

    assert reference == ArtifactDocumentReference(
        document_id="run-1:artifact:1:lesson-1",
        artifact_id="lesson-1",
        artifact_type="lesson",
        generation_id="run-1:artifact:1",
        version=1,
        title="Fractions lesson",
    )
    assert "sections" not in reference.as_state()
    assert await store.read_projection(reference.document_id) == _artifact()


def test_current_generation_references_exclude_stale_cycle_results() -> None:
    references = [
        ArtifactDocumentReference(
            document_id="run-1:artifact:1:lesson-1",
            artifact_id="lesson-1",
            artifact_type="lesson",
            generation_id="run-1:artifact:1",
            version=1,
            title="Old lesson",
        ).as_state(),
        ArtifactDocumentReference(
            document_id="run-1:artifact:2:lesson-1",
            artifact_id="lesson-1",
            artifact_type="lesson",
            generation_id="run-1:artifact:2",
            version=2,
            title="Current lesson",
        ).as_state(),
    ]

    current = current_generation_artifact_references(references, "run-1:artifact:2")

    assert current == [references[1]]
