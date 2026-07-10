"""Thin-state artifact content boundary for the teaching-pack graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, TypedDict

from common.contracts.artifact import ArtifactContent

if TYPE_CHECKING:
    from langgraph.store.base import BaseStore


class ArtifactDocumentReferenceState(TypedDict):
    """The compact artifact identity persisted in LangGraph checkpoints."""

    document_id: str
    artifact_id: str
    artifact_type: str
    generation_id: str
    version: int
    title: str


@dataclass(frozen=True, slots=True)
class ArtifactDocumentReference:
    """Reference to one generated artifact projection outside graph state."""

    document_id: str
    artifact_id: str
    artifact_type: str
    generation_id: str
    version: int
    title: str

    def as_state(self) -> ArtifactDocumentReferenceState:
        """Encode the reference into the JSON-compatible graph state shape."""
        return {
            "document_id": self.document_id,
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "generation_id": self.generation_id,
            "version": self.version,
            "title": self.title,
        }


class ArtifactContentStore(Protocol):
    """Package-owned port for durable artifact projections."""

    async def persist(
        self,
        run_id: str,
        generation_id: str,
        artifact: ArtifactContent,
        artifact_id: str,
    ) -> ArtifactDocumentReference:
        """Persist a generated projection and return its compact reference."""
        ...

    async def read_projection(self, document_id: str) -> ArtifactContent:
        """Load a full artifact projection outside the graph checkpoint."""
        ...

    async def read_projections(
        self,
        references: list[ArtifactDocumentReferenceState],
    ) -> list[ArtifactContent]:
        """Load referenced projections in deterministic checkpoint order."""
        ...


class InMemoryArtifactContentStore:
    """Deterministic adapter for tests and isolated package execution."""

    def __init__(self) -> None:
        self._projections: dict[str, ArtifactContent] = {}

    async def persist(
        self,
        run_id: str,
        generation_id: str,
        artifact: ArtifactContent,
        artifact_id: str,
    ) -> ArtifactDocumentReference:
        _ = run_id
        document_id = f"{generation_id}:{artifact_id}"
        self._projections[document_id] = artifact
        return ArtifactDocumentReference(
            document_id=document_id,
            artifact_id=artifact_id,
            artifact_type=artifact.artifact_type,
            generation_id=generation_id,
            version=1,
            title=artifact.title,
        )

    async def read_projection(self, document_id: str) -> ArtifactContent:
        return self._projections[document_id]

    async def read_projections(
        self,
        references: list[ArtifactDocumentReferenceState],
    ) -> list[ArtifactContent]:
        return [await self.read_projection(reference["document_id"]) for reference in references]


class LangGraphArtifactContentStore:
    """Durable LangGraph-store adapter composed by the gateway runtime."""

    def __init__(self, store: BaseStore) -> None:
        self._store = store

    async def persist(
        self,
        run_id: str,
        generation_id: str,
        artifact: ArtifactContent,
        artifact_id: str,
    ) -> ArtifactDocumentReference:
        document_id = f"{generation_id}:{artifact_id}"
        self._store.put(
            _artifact_namespace(run_id),
            document_id,
            artifact.model_dump(mode="json"),
        )
        return ArtifactDocumentReference(
            document_id=document_id,
            artifact_id=artifact_id,
            artifact_type=artifact.artifact_type,
            generation_id=generation_id,
            version=1,
            title=artifact.title,
        )

    async def read_projection(self, document_id: str) -> ArtifactContent:
        run_id = document_id.split(":artifact:", maxsplit=1)[0]
        item = self._store.get(_artifact_namespace(run_id), document_id)
        if item is None:
            raise KeyError(document_id)
        return ArtifactContent.model_validate(item.value)

    async def read_projections(
        self,
        references: list[ArtifactDocumentReferenceState],
    ) -> list[ArtifactContent]:
        return [await self.read_projection(reference["document_id"]) for reference in references]


def _artifact_namespace(run_id: str) -> tuple[str, str]:
    return (run_id, "artifact_projections")
