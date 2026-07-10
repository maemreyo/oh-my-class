# ADR-052: ArtifactDocument, Stable Identity, Answer Separation, and Variants

## Status

**Accepted** (2026-07-10) — Replace open-ended production artifact dictionaries with a versioned `ArtifactDocument` envelope containing discriminated typed payloads, stable content identities, separate answer data, and explicit variant lineage.

## Context

The current canonical generation contract uses `ArtifactContent.sections: list[dict]`. Typed components are validated when present, but arbitrary section shapes remain possible. That flexibility prevents a safe full-breadth structured editor, stable scoped regeneration, reliable dependency invalidation, exact version comparison, and exporter capability validation.

At the same time, forcing lessons, assessments, and slide decks into one flat generic block tree would erase important domain models such as `SlideDeckData`. A common lifecycle is needed without flattening specialized payloads.

Answer data presents a separate safety problem. Student-facing output must not contain correct answers in hidden JSON, DOM, data attributes, or export payloads. A projection that merely strips teacher-only fields is weaker than a canonical model that never puts answer data in the student document.

## Decision

### `ArtifactDocument` is the canonical envelope

Every new generated or edited artifact version is an `ArtifactDocument` with shared fields for:

- artifact and document identity;
- artifact kind and typed payload discriminator;
- version and parent lineage;
- canonical language and optional source-language version;
- audience policy;
- source, asset, and dependency references;
- generation and edit authority;
- content, schema, prompt, model-policy, and knowledge versions;
- quality and approval status references.

The payload is a discriminated typed union, not an arbitrary dictionary. Initial payload families include:

- `BlockDocument` for lesson-like and synthesis surfaces;
- `AssessmentDocument` for question-bearing student artifacts;
- `SlideDeckData` for presentation content;
- other specialized typed payloads where a universal block tree would be lossy.

Renderer, editor, quality, and exporter registries adapt each payload through declared capabilities.

### Twelve core artifact surfaces

Full-Breadth V1 supports these artifact surfaces:

1. `lesson`
2. `worksheet`
3. `quiz`
4. `drill`
5. `recap`
6. `infographic`
7. `flashcard_deck`
8. `answer_key`
9. `roadmap`
10. `slide_deck`
11. `exit_ticket`
12. `reading_passage`

`teaching_pack` is a composite projection of approved artifact versions, not an independently authored artifact.

### Stable identity exists at every editable level

Stable Content Entity IDs are required for:

- document;
- section or slide;
- block;
- question or item;
- option, pair, blank, ordering member, or rubric criterion;
- asset reference.

Compatible regeneration preserves an ID when the semantic entity remains the same. Replacement of the entity creates a new ID. Scoped editing, review notes, dependency edges, answer links, analytics, and version lineage address entities by ID rather than list index or text hash.

### Immutable content versions

Every accepted generation, manual edit, AI-assisted edit, translation, restoration, or semantic adaptation creates an immutable version with parent lineage and authority metadata. Restore creates a new version copying an older payload; it does not mutate history.

One canonical language is stored per version. Translation creates a derived **Language Version** with independent quality and approval state. Bilingual content is permitted only when explicitly requested and supported by the payload contract.

### Answers are separate by construction

Question-bearing specialists produce an atomic result containing:

- a student-safe `AssessmentDocument`; and
- a teacher-only, versioned `AnswerSet` linked by Content Entity IDs.

The student payload never includes correct answers or teacher explanations, including hidden fields. Trusted scoring and export adapters join the `AnswerSet` only at a teacher-only boundary.

The `answer_key` surface is a derived teacher artifact rendered from one or more `AnswerSet` versions. It has its own snapshot, approval, and export status, but it is not generated independently in a way that can drift from its questions.

A semantic question edit invalidates its linked answer entity and every dependent answer-key projection.

### Variants are explicit and bounded

Semantic support, challenge, language scaffold, and accessibility adaptations are typed **Content Variants** with source lineage, quality state, and approval state.

Variants are generated on demand, except where the Teaching Brief or Class Profile marks one required. Pure render/theme changes such as high contrast may be projections without a new semantic content version. Reading simplification, changed vocabulary, altered task difficulty, or additional scaffolding always create a semantic variant version.

### Dependency-aware invalidation

Semantic edits do not mutate or delete previous outputs. The dependency graph marks affected artifacts, `AnswerSet`s, variants, snapshots, and exports stale. The teacher sees impact before scoped regeneration or reapproval. The system never silently regenerates dependent content.

### Read-old, write-new migration

New Creator runs write `ArtifactDocument` only. Existing persisted `ArtifactContent` remains readable through bounded adapters during migration. There is no long-lived dual write. Renderer, preview, and export readers support old persisted records until the stabilization and cleanup window closes.

## Consequences

- Structured editing, exact lineage, scoped review, and dependency repair become safe and addressable.
- Specialized models remain deep instead of being flattened into a weak universal schema.
- Answer leakage becomes structurally harder, not merely a projection convention.
- Contract migration touches Python contracts, generated Zod, persistence, specialists, renderer, editor, quality, and exporters.
- Existing arbitrary section fixtures need read adapters or migration evidence; new production generation cannot emit unknown shapes.

## Considered Options

- **Keep flexible `sections` dictionaries**: rejected because the editor and dependency model cannot be made reliable around unstable paths.
- **One universal recursive block tree**: rejected because slide and assessment semantics would become shallow and validation would weaken.
- **Completely unrelated per-artifact models**: rejected because lifecycle, identity, provenance, and approval would fragment.
- **Answers in teacher-only fields of student JSON**: rejected because stripping failures can leak scrapeable answer data.
- **Dual-write old and new contracts**: rejected because it creates two authorities and permanent drift pressure.

## References

- ADR-008 Artifact Workflow and Rendered Snapshots
- ADR-012 Data Governance and Versioning
- ADR-025 Renderer Artifact-Kind Plugin Registry Rewrite
- ADR-040 Native Slide Deck Artifact and SlideDeckEngine
- ADR-042 Slide Deck Surfaces, Quality Gates, and Release Evidence
- ADR-047 Slide Deck In-Browser Editor and AI-Assisted Revision
