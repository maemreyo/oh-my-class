"""Language Versions and typed Content Variants (#451, ADR-052/ADR-055).

A Language Version (a translation) and a typed Content Variant (semantic
support, challenge, language scaffold, or accessibility adaptation) are both
*semantic* derivations: they change what the content says, not how it looks.
Each therefore gets its own artifact lineage -- its own `artifact_id`, its
own version chain, its own independent approval -- rather than becoming a
new version of the source artifact, so a teacher can approve the Vietnamese
translation without that decision being conflated with approving the
English original, and re-generating a scaffold later doesn't clobber the
source's own edit history.

This is deliberately distinct from a *theme-only projection* (e.g. the
high-contrast-dyslexia theme in `packages/renderer`), which changes how
already-approved content is displayed and therefore never creates a new
`ArtifactDocument` version at all -- it's a render-time parameter. Routing
an accessibility need through this module means "the words themselves must
change" (added alt text, simplified sentence structure); routing it through
the renderer's theme system means "only the presentation changes." Conflating
the two would mean re-approving content that never semantically changed, or
worse, silently reusing unapproved semantic changes as if they were a theme.

Re-deriving (e.g. re-translating after the English source was edited) adds a
new version to the *existing* derived lineage rather than starting a fresh
one, so the derived artifact keeps one continuous, independently-approvable
history of its own -- exactly like `edit_artifact_document` does for direct
edits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import select

from common.contracts.artifact_document import ArtifactDocument, ArtifactPayload, DocumentLanguage
from services.gateway.artifact_document_edit_service import (
    ArtifactHasNoVersionsError,
    impacted_artifact_ids,
)
from services.gateway.artifact_document_models import ContentVariantRecord
from services.gateway.artifact_document_store import (
    ArtifactDocumentStore,
    ArtifactDocumentWrite,
    ContentDependencyCreate,
    ContentVariantCreate,
    VariantKind,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from services.gateway.teaching_pack_types import RunId


class LanguageVersionAlreadyInTargetLanguageError(ValueError):
    """Raised when asked to translate an artifact into its own current language."""

    def __init__(self, artifact_id: str, language: str) -> None:
        self.artifact_id = artifact_id
        self.language = language
        super().__init__(f"{artifact_id} is already in {language}")


@dataclass(frozen=True, slots=True)
class DerivedVersionOutcome:
    document: ArtifactDocument
    impacted_artifact_ids: list[str]


def _derived_artifact_id(source_artifact_id: str, *, suffix: str) -> str:
    """One canonical derived-lineage id per (source, suffix) -- deterministic
    so re-deriving finds and extends the same lineage instead of forking a
    new one every call."""
    return f"{source_artifact_id}--{suffix}"[:80]


async def _persist_or_extend_derived_lineage(
    session: AsyncSession,
    *,
    run_id: RunId,
    source_artifact_id: str,
    derived_artifact_id: str,
    language: DocumentLanguage,
    authority: str,
    payload: ArtifactPayload,
    dependency_kind: str,
    variant: ContentVariantCreate | None,
) -> DerivedVersionOutcome:
    store = ArtifactDocumentStore(session)
    source_latest = await store.get_latest(run_id, source_artifact_id)
    if source_latest is None:
        raise ArtifactHasNoVersionsError(source_artifact_id)

    derived_latest = await store.get_latest(run_id, derived_artifact_id)
    document = ArtifactDocument(
        document_id=f"doc-{uuid4().hex[:16]}",
        artifact_id=derived_artifact_id,
        artifact_type=source_latest.artifact_type,  # type: ignore[arg-type]
        version=(derived_latest.version + 1) if derived_latest is not None else 1,
        language=language,
        audience=source_latest.audience,  # type: ignore[arg-type]
        authority=authority,  # type: ignore[arg-type]
        payload=payload,
        parent_document_id=derived_latest.document_id if derived_latest is not None else None,
        source_document_id=source_latest.document_id,
    )
    write = ArtifactDocumentWrite(
        run_id=run_id,
        document=document,
        variant=variant,
        dependencies=(ContentDependencyCreate(
            source_document_id=source_latest.document_id, dependency_kind=dependency_kind,  # type: ignore[arg-type]
        ),),
    )
    if derived_latest is None:
        persisted = await store.persist(write)
    else:
        persisted = await store.create_edit(run_id, derived_latest.version, write)
    impacted = await impacted_artifact_ids(session, source_latest.document_id)
    return DerivedVersionOutcome(document=persisted.document, impacted_artifact_ids=impacted)


async def create_language_version(
    session: AsyncSession,
    *,
    run_id: RunId,
    source_artifact_id: str,
    target_language: DocumentLanguage,
    payload: ArtifactPayload,
    authority: str = "translated",
) -> DerivedVersionOutcome:
    """Create (or extend) the translation lineage for `source_artifact_id` in
    `target_language`. Independent approval falls out for free: the derived
    artifact_id has its own version head, so `approve_artifact_version` on it
    never touches the source's approval status."""
    store = ArtifactDocumentStore(session)
    source_latest = await store.get_latest(run_id, source_artifact_id)
    if source_latest is None:
        raise ArtifactHasNoVersionsError(source_artifact_id)
    if source_latest.language == target_language:
        raise LanguageVersionAlreadyInTargetLanguageError(source_artifact_id, target_language)
    return await _persist_or_extend_derived_lineage(
        session,
        run_id=run_id,
        source_artifact_id=source_artifact_id,
        derived_artifact_id=_derived_artifact_id(source_artifact_id, suffix=f"lang-{target_language}"),
        language=target_language,
        authority=authority,
        payload=payload,
        dependency_kind="translation",
        variant=None,
    )


async def create_content_variant(
    session: AsyncSession,
    *,
    run_id: RunId,
    source_artifact_id: str,
    variant_kind: VariantKind,
    payload: ArtifactPayload,
    authority: str = "variant_generated",
) -> DerivedVersionOutcome:
    """Create (or extend) one typed content variant's lineage. The variant
    keeps the source's language -- a scaffold/challenge/accessibility variant
    is a semantic adaptation, not a translation; combine both by calling
    `create_language_version` on the variant's own artifact_id if a
    translated variant is ever needed."""
    store = ArtifactDocumentStore(session)
    source_latest = await store.get_latest(run_id, source_artifact_id)
    if source_latest is None:
        raise ArtifactHasNoVersionsError(source_artifact_id)
    derived_artifact_id = _derived_artifact_id(source_artifact_id, suffix=f"variant-{variant_kind}")
    return await _persist_or_extend_derived_lineage(
        session,
        run_id=run_id,
        source_artifact_id=source_artifact_id,
        derived_artifact_id=derived_artifact_id,
        language=source_latest.language,  # type: ignore[arg-type]
        authority=authority,
        payload=payload,
        dependency_kind="variant",
        variant=ContentVariantCreate(
            variant_id=f"variant-{uuid4().hex[:16]}",
            variant_kind=variant_kind,
            source_document_id=source_latest.document_id,
        ),
    )


# Accessibility is never optional: WCAG-adapted content is a release
# requirement (ADR-058), not a differentiated-instruction convenience.
# Language scaffolds are required specifically when the class is being
# taught content in a language other than its instruction language (EFL/ESL,
# per #449) -- everyone in that class needs the scaffold, not just some
# students. Challenge and semantic-support extensions stay recommendations:
# they target a subset of students the teacher identifies, not the whole
# class, so auto-generating them for every artifact would be noise.
_ALWAYS_REQUIRED: frozenset[VariantKind] = frozenset({"accessibility"})


def required_variant_kinds(class_profile: dict[str, object]) -> list[VariantKind]:
    """Which variant kinds must exist before an artifact can be released to
    this class, versus which stay on-demand recommendations (#451 AC)."""
    required: set[VariantKind] = set(_ALWAYS_REQUIRED)
    target_language = class_profile.get("target_language")
    instruction_language = class_profile.get("instruction_language")
    if target_language and instruction_language and target_language != instruction_language:
        required.add("language_scaffold")
    return sorted(required)


_ALL_VARIANT_KINDS: tuple[VariantKind, ...] = (
    "semantic_support", "challenge", "language_scaffold", "accessibility",
)


@dataclass(frozen=True, slots=True)
class RequiredVariantsOutcome:
    created: list[VariantKind]
    already_present: list[VariantKind]
    missing_payload: list[VariantKind]
    recommended: list[VariantKind]


async def ensure_required_variants(
    session: AsyncSession,
    *,
    run_id: RunId,
    source_artifact_id: str,
    class_profile: dict[str, object],
    payload_by_kind: dict[VariantKind, ArtifactPayload],
) -> RequiredVariantsOutcome:
    """Auto-generate every required variant kind not yet present; every other
    kind is surfaced as a recommendation only, never generated automatically
    (#451 AC: required variants auto-generate, optional ones stay
    recommendations). Callers supply the already-adapted payload per kind --
    deciding *how* to adapt content is a specialist/authoring concern, not
    this data-layer policy."""
    required = set(required_variant_kinds(class_profile))
    present = await _variant_kinds_present(session, run_id, source_artifact_id)
    created: list[VariantKind] = []
    missing_payload: list[VariantKind] = []
    for kind in sorted(required - present):
        payload = payload_by_kind.get(kind)
        if payload is None:
            missing_payload.append(kind)
            continue
        await create_content_variant(
            session, run_id=run_id, source_artifact_id=source_artifact_id, variant_kind=kind, payload=payload,
        )
        created.append(kind)
    return RequiredVariantsOutcome(
        created=created,
        already_present=sorted(required & present),
        missing_payload=missing_payload,
        recommended=sorted(kind for kind in _ALL_VARIANT_KINDS if kind not in required),
    )


async def _variant_kinds_present(
    session: AsyncSession, run_id: RunId, source_artifact_id: str,
) -> set[VariantKind]:
    store = ArtifactDocumentStore(session)
    source_latest = await store.get_latest(run_id, source_artifact_id)
    if source_latest is None:
        return set()
    statement = select(ContentVariantRecord.variant_kind).where(
        ContentVariantRecord.source_document_id == source_latest.document_id,
    )
    rows = (await session.execute(statement)).scalars().all()
    return {kind for kind in rows}  # type: ignore[misc]
