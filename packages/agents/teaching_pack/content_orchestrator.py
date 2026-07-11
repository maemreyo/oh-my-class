"""Thin-state artifact content boundary for the teaching-pack graph.

Naming note (#464): this module predates ADR-053 and owns only the
*persistence* port (`ArtifactContentStore` and its adapters) -- it is not
the ADR-053 "Content Orchestrator" (that responsibility -- capability
resolution, dependency planning, dispatch -- lives in
`specialist_capability.py`, `common.contracts.dependency_plan`, and
`generate_one_artifact.py`). `ArtifactPersistenceResult` below is aliased as
`SpecialistResult` so ADR-053's contract vocabulary is directly importable
without a parallel, duplicate type.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, TypedDict

from common.contracts.answer_set import AnswerSet
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


@dataclass(frozen=True, slots=True)
class ArtifactPersistenceResult:
    artifact: ArtifactContent
    answer_set: AnswerSet | None = None
    dependency_document_ids: tuple[str, ...] = ()


# #464: ADR-053 names this "SpecialistResult" -- an alias, not a parallel
# type, so both vocabularies resolve to the one real, tested implementation.
SpecialistResult = ArtifactPersistenceResult


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

    async def persist_result(
        self,
        run_id: str,
        generation_id: str,
        result: ArtifactPersistenceResult,
        artifact_id: str,
    ) -> ArtifactDocumentReference:
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

    async def read_answer_set(self, document_id: str) -> AnswerSet | None:
        ...


class InMemoryArtifactContentStore:
    """Deterministic adapter for tests and isolated package execution."""

    def __init__(self) -> None:
        self._projections: dict[str, ArtifactContent] = {}
        self._answer_sets: dict[str, AnswerSet] = {}

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

    async def persist_result(
        self,
        run_id: str,
        generation_id: str,
        result: ArtifactPersistenceResult,
        artifact_id: str,
    ) -> ArtifactDocumentReference:
        reference = await self.persist(run_id, generation_id, _student_projection(result.artifact, artifact_id), artifact_id)
        if result.answer_set is not None:
            self._answer_sets[reference.document_id] = result.answer_set.model_copy(update={
                "source_document_id": reference.document_id,
                "source_version": reference.version,
                "answer_set_id": f"answers-{reference.document_id}-v{reference.version}",
            })
        return reference

    async def read_projection(self, document_id: str) -> ArtifactContent:
        return self._projections[document_id]

    async def read_projections(
        self,
        references: list[ArtifactDocumentReferenceState],
    ) -> list[ArtifactContent]:
        return [await self.read_projection(reference["document_id"]) for reference in references]

    async def read_answer_set(self, document_id: str) -> AnswerSet | None:
        return self._answer_sets.get(document_id)


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

    async def persist_result(
        self,
        run_id: str,
        generation_id: str,
        result: ArtifactPersistenceResult,
        artifact_id: str,
    ) -> ArtifactDocumentReference:
        reference = await self.persist(run_id, generation_id, _student_projection(result.artifact, artifact_id), artifact_id)
        if result.answer_set is not None:
            self._store.put(
                _answer_set_namespace(run_id),
                reference.document_id,
                result.answer_set.model_copy(update={
                    "source_document_id": reference.document_id,
                    "source_version": reference.version,
                    "answer_set_id": f"answers-{reference.document_id}-v{reference.version}",
                }).model_dump(mode="json"),
            )
        return reference

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

    async def read_answer_set(self, document_id: str) -> AnswerSet | None:
        run_id = document_id.split(":artifact:", maxsplit=1)[0]
        item = self._store.get(_answer_set_namespace(run_id), document_id)
        return AnswerSet.model_validate(item.value) if item is not None else None


def _artifact_namespace(run_id: str) -> tuple[str, str]:
    return (run_id, "artifact_projections")


def _answer_set_namespace(run_id: str) -> tuple[str, str]:
    return (run_id, "artifact_answer_sets")


def _student_projection(artifact: ArtifactContent, artifact_id: str) -> ArtifactContent:
    from common.contracts.artifact_projection_mapper import artifact_content_from_document, artifact_document_from_content

    document = artifact_document_from_content(
        artifact,
        document_id="student-projection",
        artifact_id=artifact_id,
    )
    return artifact_content_from_document(document)
