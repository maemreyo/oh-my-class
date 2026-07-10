# ADR-056: Capability Truth for Rendering, Exports, Media, and Live Delivery

## Status

**Accepted** (2026-07-10) — Make every declared render, export, media, and live-delivery capability explicit, typed, truthful, and verified through its real surface.

## Context

The repository currently has broader contract and path declarations than uniformly real implementations. Renderer plugins, exporter facades, gateway subprocess bridges, and documentation do not always agree. A Full-Breadth V1 cannot return plausible file paths, skeleton archives, silent lossy conversions, or generic template fallbacks and still claim capability completeness.

Artifact richness also creates media and licensing pressure. The offline invariant forbids remote assets, while teachers may still benefit from external visual references. Live slide delivery must pin approved content rather than creating another mutable content authority.

## Decision

### Twelve artifact surfaces must render through declared plugins

Every core artifact surface has a registered renderer capability with:

- accepted `ArtifactDocument` payload type;
- teacher/student/print audience support;
- template and sanitizer policy;
- theme and accessibility behavior;
- managed-script declaration where needed;
- standalone and print capability;
- versioned render manifest.

Unknown artifact kinds or unsupported payloads fail explicitly. They never fall back to a lesson renderer or a generic HTML template.

`teaching_pack` remains a composite projection that pins exact approved artifact version IDs.

### All seven declared export formats are real release blockers

Full-Breadth V1 must implement and verify:

1. standalone HTML
2. Moodle GIFT
3. H5P
4. QTI
5. Anki APKG
6. Flashcard TSV
7. PPTX

No format may return a fake path, placeholder archive, unsupported skeleton, or best-effort success. `google_forms` remains a separate Publish Target, not an offline `ExportFormat`.

### Typed Export Capability Matrix

Full breadth does not mean every artifact converts to every format. A versioned **Export Capability Matrix** declares:

- supported artifact and question capabilities;
- required source artifacts or `AnswerSet`s;
- lossless versus explicitly degraded behavior;
- unsupported combinations;
- file validation and external import smoke requirements.

Unsupported pairs are rejected during scope resolution or export selection with actionable alternatives. Optional degradation requires a declared capability and teacher-visible warning; it is never inferred by an exporter.

Every supported matrix entry is release-tested through the real file surface. Every unsupported entry fails clearly.

### Immutable exports and explicit regeneration

Every export record pins source artifact, `AnswerSet`, language, variant, snapshot, renderer, exporter, and capability-matrix versions. Existing downloads remain immutable and accessible after edits.

Dependency changes mark affected format entries stale. The workspace shows a stale matrix and lets the teacher regenerate affected exports or all requested exports. Regeneration reuses unaffected files. Exports are never overwritten, auto-deleted, or automatically regenerated after an edit.

### Offline-safe visual policy

Production artifacts may use:

- teacher-uploaded Media Asset Versions;
- local governed icon and diagram registries;
- deterministic or schema-bound generated inline SVG passed through sanitization;
- CSS shapes and patterns;
- data URIs within policy limits.

They may not use remote images, fonts, scripts, styles, iframes, or external media embeds.

Research may produce **Visual Source Suggestions**. A suggestion is not an artifact asset. The teacher must review licensing, download the visual, and upload it to the Media Library before it can be referenced in an export.

Media assets are immutable versions with ownership scope, source or license note, checksum, and alt-text status. Artifact blocks store a specific asset reference. Replacement creates a new asset version and dependency impact. Asset bytes are not sent to an LLM unless an explicit, privacy-approved multimodal task requires them.

### Provenance and licensing manifests

Internal manifests record generated, teacher-edited, AI-rewritten, and source-derived authority at block or payload granularity, along with model, prompt, schema, source, and asset-license versions.

The product does not automatically apply an open license to generated content. Teachers or organizations may choose a sharing license, but they cannot override third-party source or asset attribution obligations. Teacher-facing exports may include an optional attribution appendix.

### Live session publication pins approved slide versions

Creator V1 may publish an approved, current `slide_deck` version into a Teaching Session. Linked activities may be attached as resources, but other artifacts do not become independent live runtimes in V1.

The Teaching Session pins the exact approved slide version. Runtime branch selections and AI suggestions create session events or an explicit proposal to fork changes back into the Creator. Live delivery never mutates the canonical pack silently.

## Consequences

- Contract declarations become product truth instead of aspirations.
- Export support is semantically honest without requiring nonsensical Cartesian conversions.
- Teachers can use external visual research without violating offline, privacy, or licensing constraints.
- Edits and live delivery remain reproducible because exact source versions are pinned.
- V1 release is blocked until QTI and every other declared format is a real, validated implementation.

## Considered Options

- **Support every artifact × export pair**: rejected because many combinations have no honest semantics.
- **Best-effort exporters**: rejected because omitted or altered teaching content can go unnoticed.
- **Remove incomplete formats from V1**: rejected by the Full-Breadth V1 scope decision.
- **Automatic stock-image download and embedding**: rejected because license, offline, security, and support complexity become product liabilities.
- **Image-generation provider integration**: deferred because it adds paid cost, moderation, provenance, and asset support complexity.
- **Live sessions mutate the pack**: rejected because classroom runtime behavior must not become an unaudited content authoring path.

## References

- ADR-023 Artifact UI Layer from Template Corpus
- ADR-025 Renderer Artifact-Kind Plugin Registry Rewrite
- ADR-030 Full Artifact-Type and Export Coverage
- ADR-042 Slide Deck Surfaces, Quality Gates, and Release Evidence
- ADR-045 Slide Deck as Teaching Session Foundation
- ADR-046 Teaching Session Platform for Slide Deck Delivery
- ADR-047 Slide Deck In-Browser Editor and AI-Assisted Revision
