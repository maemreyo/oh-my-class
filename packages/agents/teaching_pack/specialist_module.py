"""#464 (ADR-053 Content Orchestrator): the `SpecialistModule` protocol.

`specialist_capability.py` already owns fail-closed *code*-capability
resolution (registered vs native vs unsupported) and
`content_coverage_resolution.py` already owns *curriculum* coverage per
subject/grade band. This module is the third, distinct thing the issue asks
for: a per-artifact-type declaration of subject/grade/language/payload/
quality capabilities, the `ContentBrief` fields a specialist consumes, and
the lineage record a generation returns -- plus a thin `SpecialistModule`
wrapper so that declaration is actually checked against something callable,
not a floating, uncalled description.

Honesty notes (do not remove without re-verifying against the real code):

- None of the ten registered specialists (`specialist_registry.py`) branch
  on subject or grade band today -- `specialist_capability.py`'s own
  docstring says the same. Declaring "all subjects, all grade bands, en+vi"
  below is therefore the accurate declaration, not a placeholder.
- `quality_criteria` are the real rubric criterion names from
  `packages/quality/layer4_judge/rubric_selector.py`'s `_BASE_CRITERIA`
  (`format_compliance`, `content_quality`, `presentation`) -- every artifact
  type uses all three (with type-specific weight overrides), so declaring
  all three for every module is accurate, not fabricated.
- `consumed_content_brief_fields` is `()` for every module: dispatch
  (`generate_one_artifact.py`) still passes raw `lesson_plan`/`research_brief`
  dicts, never a `ContentBrief`. Threading `ContentBrief` into live dispatch
  is a separate, larger integration this module does not claim to have done
  -- `SpecialistRequest.content_brief` exists so a specialist can start
  reading typed fields without a second contract migration once that lands.
"""

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
from packages.agents.teaching_pack.specialist_registry import (
    SPECIALIST_REGISTRY,
    ArtifactSpecialist,
)

if TYPE_CHECKING:
    from common.contracts.content_brief import ContentBrief

# Real rubric criterion names (packages/quality/layer4_judge/rubric_selector.py
# `_BASE_CRITERIA`) -- every artifact type is judged against all three.
_QUALITY_CRITERIA: tuple[str, ...] = ("format_compliance", "content_quality", "presentation")

# All nine canonical subjects and both language codes: no specialist restricts
# either today, so declaring the full set is the accurate claim.
_ALL_SUBJECTS: tuple[str, ...] = tuple(sorted(key.value for key in SubjectKey))
_ALL_GRADE_BANDS: tuple[str, ...] = tuple(band.value for band in GradeBand)
_ALL_LANGUAGES: tuple[str, ...] = ("en", "vi")


@dataclass(frozen=True, slots=True)
class SpecialistRequest:
    """ADR-053 `SpecialistRequest`: what one specialist call receives.

    Wraps the same two dicts specialists already take (`lesson_plan`,
    `research_brief`) rather than a raw positional call -- a typed request
    object, not an open dictionary passed by convention. `content_brief` is
    optional and unused by every specialist today (see module docstring).
    """

    artifact_type: str
    lesson_plan: dict[str, Any]
    research_brief: dict[str, Any]
    content_brief: ContentBrief | None = None


@dataclass(frozen=True, slots=True)
class SpecialistLineage:
    """ADR-053 "provenance required by downstream quality and approval":
    which module, at which version, generated an artifact, and which
    `ContentBrief` fields it declares it consumed."""

    artifact_type: str
    specialist_id: str
    module_version: str
    consumed_content_brief_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SpecialistModuleDeclaration:
    """Declared subject/grade/language/payload/quality capabilities for one
    artifact type, plus the `ContentBrief` fields it consumes."""

    artifact_type: str
    family: SpecialistFamily
    payload_kind: PayloadKind
    subjects: tuple[str, ...]
    grade_bands: tuple[str, ...]
    languages: tuple[str, ...]
    quality_criteria: tuple[str, ...]
    consumed_content_brief_fields: tuple[str, ...] = ()
    module_version: str = "v1"


class SpecialistModule(Protocol):
    """A deep module wrapping one artifact type's generation policy."""

    @property
    def declaration(self) -> SpecialistModuleDeclaration: ...

    def generate(self, request: SpecialistRequest) -> dict[str, Any]:
        """Run generation. Raises for a natively-dispatched type (its
        generation lives in a dedicated branch, e.g. `generate_one_artifact.
        _slide_deck_artifact`, not behind this uniform entry point)."""
        ...

    def lineage(self, resolution: CapabilityResolution) -> SpecialistLineage:
        """Build the provenance record for one resolved generation call."""
        ...


class NativelyDispatchedModuleError(NotImplementedError):
    """Raised by `RegisteredSpecialistModule.generate` for a natively
    dispatched artifact type (`answer_key`, `slide_deck`): those have their
    own dedicated dispatch branch in `generate_one_artifact.py` and are
    never invoked through this uniform entry point."""

    def __init__(self, artifact_type: str) -> None:
        self.artifact_type = artifact_type
        super().__init__(
            f"{artifact_type!r} is natively dispatched; call its dedicated "
            "branch in generate_one_artifact.py, not SpecialistModule.generate",
        )


@dataclass(frozen=True, slots=True)
class RegisteredSpecialistModule:
    """Concrete `SpecialistModule` wrapping one `SPECIALIST_REGISTRY` entry,
    or `None` for a natively-dispatched type."""

    declaration: SpecialistModuleDeclaration
    _callable: ArtifactSpecialist | None

    def generate(self, request: SpecialistRequest) -> dict[str, Any]:
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
    return SpecialistModuleDeclaration(
        artifact_type=artifact_type,
        family=SPECIALIST_FAMILIES[artifact_type],
        payload_kind=capability.payload_kind,
        subjects=_ALL_SUBJECTS,
        grade_bands=_ALL_GRADE_BANDS,
        languages=_ALL_LANGUAGES,
        quality_criteria=_QUALITY_CRITERIA,
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


# #464: "Register five specialist families with per-artifact adapters and
# declared subject/grade/language/payload/quality capabilities." Built once
# at import time from the existing registry/capability/family SSOTs -- never
# a second, independently-maintained list.
SPECIALIST_MODULES: dict[str, RegisteredSpecialistModule] = _build_modules()


def get_specialist_module(artifact_type: str) -> RegisteredSpecialistModule | None:
    return SPECIALIST_MODULES.get(artifact_type)
