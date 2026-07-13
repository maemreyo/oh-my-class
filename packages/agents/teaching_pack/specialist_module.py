"""Declared specialist capabilities and typed specialist adapters (ADR-053)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from common.contracts.education_policy import SubjectKey
from common.contracts.grade_band import GradeBand
from packages.agents.teaching_pack.specialist_capability import (
    NATIVELY_DISPATCHED_ARTIFACT_TYPES,
    SPECIALIST_CAPABILITIES,
    SPECIALIST_FAMILIES,
    CapabilityResolution,
    PayloadKind,
    SpecialistFamily,
)
from packages.agents.teaching_pack.specialist_registry import SPECIALIST_REGISTRY, ArtifactSpecialist

if TYPE_CHECKING:
    from common.contracts.content_brief import ContentBrief

_QUALITY_CRITERIA: tuple[str, ...] = ("format_compliance", "content_quality", "presentation")
_ALL_SUBJECTS: tuple[str, ...] = tuple(sorted(key.value for key in SubjectKey))
_ALL_GRADE_BANDS: tuple[str, ...] = tuple(band.value for band in GradeBand)
_ALL_LANGUAGES: tuple[str, ...] = ("en", "vi")
_FIELDS_BY_FAMILY: dict[SpecialistFamily, tuple[str, ...]] = {
    "lesson_design": ("objectives", "scope", "methodology", "learning_moves", "must_include", "avoid"),
    "assessment": ("objectives", "scope", "terminology", "answer_policy", "dependency_document_ids"),
    "practice": ("objectives", "scope", "methodology", "learning_moves", "answer_policy"),
    "synthesis": ("objectives", "scope", "terminology", "source_citation_ids", "must_include", "avoid"),
    "presentation": ("objectives", "scope", "methodology", "learning_moves", "source_citation_ids"),
}


@dataclass(frozen=True, slots=True)
class SpecialistRequest:
    artifact_type: str
    lesson_plan: dict[str, Any]
    research_brief: dict[str, Any]
    content_brief: ContentBrief | None = None


@dataclass(frozen=True, slots=True)
class SpecialistLineage:
    artifact_type: str
    specialist_id: str
    module_version: str
    consumed_content_brief_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SpecialistModuleDeclaration:
    artifact_type: str
    family: SpecialistFamily
    payload_kind: PayloadKind
    subjects: tuple[str, ...]
    grade_bands: tuple[str, ...]
    languages: tuple[str, ...]
    quality_criteria: tuple[str, ...]
    consumed_content_brief_fields: tuple[str, ...]
    module_version: str = "v2"


class SpecialistModule(Protocol):
    @property
    def declaration(self) -> SpecialistModuleDeclaration: ...

    def generate(self, request: SpecialistRequest) -> dict[str, Any]: ...

    def lineage(self, resolution: CapabilityResolution) -> SpecialistLineage: ...


class NativelyDispatchedModuleError(NotImplementedError):
    def __init__(self, artifact_type: str) -> None:
        self.artifact_type = artifact_type
        super().__init__(
            f"{artifact_type!r} is natively dispatched; call its dedicated branch in "
            "generate_one_artifact.py, not SpecialistModule.generate",
        )


@dataclass(frozen=True, slots=True)
class RegisteredSpecialistModule:
    declaration: SpecialistModuleDeclaration
    _callable: ArtifactSpecialist | None

    def generate(self, request: SpecialistRequest) -> dict[str, Any]:
        if request.artifact_type != self.declaration.artifact_type:
            raise ValueError(
                f"specialist module {self.declaration.artifact_type!r} received "
                f"request for {request.artifact_type!r}",
            )
        if request.content_brief is not None and str(request.content_brief.artifact_type) != request.artifact_type:
            raise ValueError("SpecialistRequest ContentBrief artifact_type mismatch")
        if self._callable is None:
            raise NativelyDispatchedModuleError(self.declaration.artifact_type)
        return self._callable(request.lesson_plan, request.research_brief)

    def lineage(self, resolution: CapabilityResolution) -> SpecialistLineage:
        artifact_type = self.declaration.artifact_type
        specialist_id = resolution.specialist_id or f"unresolved:{artifact_type}"
        return SpecialistLineage(
            artifact_type=artifact_type,
            specialist_id=specialist_id,
            module_version=self.declaration.module_version,
            consumed_content_brief_fields=self.declaration.consumed_content_brief_fields,
        )


def _build_declaration(artifact_type: str) -> SpecialistModuleDeclaration:
    capability = SPECIALIST_CAPABILITIES[artifact_type]
    family = SPECIALIST_FAMILIES[artifact_type]
    return SpecialistModuleDeclaration(
        artifact_type=artifact_type,
        family=family,
        payload_kind=capability.payload_kind,
        subjects=_ALL_SUBJECTS,
        grade_bands=_ALL_GRADE_BANDS,
        languages=_ALL_LANGUAGES,
        quality_criteria=_QUALITY_CRITERIA,
        consumed_content_brief_fields=_FIELDS_BY_FAMILY[family],
    )


def _build_modules() -> dict[str, RegisteredSpecialistModule]:
    modules: dict[str, RegisteredSpecialistModule] = {}
    for artifact_type in SPECIALIST_CAPABILITIES:
        callable_ = SPECIALIST_REGISTRY.get(artifact_type)
        if artifact_type in NATIVELY_DISPATCHED_ARTIFACT_TYPES:
            callable_ = None
        modules[artifact_type] = RegisteredSpecialistModule(
            declaration=_build_declaration(artifact_type),
            _callable=callable_,
        )
    return modules


SPECIALIST_MODULES: dict[str, RegisteredSpecialistModule] = _build_modules()


def get_specialist_module(artifact_type: str) -> RegisteredSpecialistModule | None:
    return SPECIALIST_MODULES.get(artifact_type)
