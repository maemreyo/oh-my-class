# ADR-055: Creator Workspace, Structured Editing, and Approval

## Status

**Accepted** (2026-07-10) — Define one persistent Creator Workspace with typed artifact editing, authority-aware AI revision, dependency impact, decision provenance, review notes, and artifact-level approval.

## Context

The existing teacher experience exposes run progress, rendered previews, scoped regeneration, and a slide-specific editor, but the full teaching-content lifecycle is split across surfaces and ordinary artifacts lack a safe common editing model. A stage wizard would mirror graph internals rather than the teacher's continuing work. A freeform WYSIWYG or raw JSON editor would break typed contracts, audience safety, renderer guarantees, and reproducible exports.

The Creator must also distinguish draft work from immutable content history, teacher authority from machine authority, and current outputs from stale dependencies and exports.

## Decision

### Persistent workspace

The Creator Workspace keeps one continuing run context with:

- Teaching Brief and resolved contract;
- blueprint, component strategy, and Planning Review;
- progressive generation status and first reviewable artifacts;
- artifact canvas with tabs or equivalent navigation;
- source, quality, and Decision Provenance inspector;
- structured editor and AI rewrite actions;
- review notes, versions, approval, variants, exports, and live-session publication.

Stage progress may be visible, but normal work is not forced through a step-by-step wizard. Wizard onboarding may exist for first use only.

### Decision Provenance, not hidden reasoning

Teacher-visible provenance includes:

- resolved inputs and policy overrides;
- source evidence and audience-adaptive citations;
- concise strategy rationale;
- specialist and Subject Capability Pack used;
- family scorecard, warnings, fallbacks, and degraded capabilities;
- version, authority, dependency, and export lineage;
- why an artifact changed or became stale.

The workspace does not expose raw prompts, chain-of-thought, provider traces, or internal graph state. Administrative diagnostics remain separate, audited, and redacted.

### Structured Artifact Editor

Every artifact surface uses a registry adapter over its typed `ArtifactDocument` payload. Teachers edit sections, blocks, questions, options, pairs, slides, interactions, and asset references through structured controls. Raw HTML and arbitrary CSS are not editable.

The Teaching Brief autosaves as a server-side draft before launch. Content edits buffer locally with crash recovery and create one immutable version only on explicit Save or navigation confirmation. AI suggestions are ephemeral until accepted.

Optimistic concurrency uses `base_version_id`. A stale save returns a conflict requiring reload or explicit reconciliation. V1 does not implement real-time cursor collaboration or CRDT editing.

### AI-assisted rewrite is scoped and confirmed

AI rewrite defaults to one block or question. Section-level rewrite requires an impact preview. Artifact-wide structural change creates a strategy revision and Planning Review. There is no one-click whole-pack rewrite.

Presets and bounded freeform guidance are supported. Every AI proposal shows before/after, remains unsaved until explicit acceptance, records `ai_assisted_edit` authority, and passes payload-specific validation and quality checks.

### Dependency-aware impact and versions

A semantic save creates a new artifact version and computes impact across dependent artifacts, `AnswerSet`s, variants, snapshots, exports, and live-session eligibility. Impact is visible before regeneration. The teacher chooses which suggested scoped repairs to run; the system never silently regenerates or replaces approved content.

Old versions remain readable and restorable. Restore creates a new version. A Forked Pack creates a new run and lineage rather than modifying the source pack.

### Artifact-level approval and review notes

Final approval applies to an artifact version. The run owner may approve, reject, or edit; explicitly delegated reviewers may act within organization policy. “Approve all current” is available when every selected artifact is current and no blocking review note remains.

V1 supports single-level anchored review notes tied to Content Entity ID and version. A note records author, status, and whether it blocks approval. Nested conversation, mentions, and real-time collaboration are outside V1.

### Audience and language surfaces

Teacher and student views are explicit projections. Student output never contains teacher-only or `AnswerSet` data. One canonical language exists per version; translation creates a new Language Version requiring quality review and approval. Bilingual mode is explicit and contract-supported.

Teacher provenance always carries claim/source mappings. Student citation presentation adapts to Grade Band and artifact pedagogy. Optional export appendices may expose citations and attribution.

### Variants and accessibility

Required semantic variants are generated when declared by the Teaching Brief or Class Profile. Other support, challenge, language scaffold, and accessibility variants are recommendations generated on demand. Theme-only accessibility projections do not create semantic versions.

The Creator Workspace targets WCAG 2.2 AA. Generated artifacts target WCAG 2.2 AA where applicable plus print, presentation, keyboard, focus, reduced-motion, semantic question, alt/long-description, contrast, and non-color-only rules. Capability exceptions are declared and visible rather than silent.

### Notifications and cancellation

External notifications are limited to action-required and milestone events: clarification, Planning Review, source conflict, content approval, escalation, first reviewable artifact, requested export ready, completion, and terminal failure. Detailed progress remains in workspace SSE.

Cancel stops future work, best-effort cancels or ignores in-flight generation by cycle ID, and preserves durable results as a **Cancelled Draft**. Passed artifacts remain viewable and forkable but unapproved; composite export is unavailable. Delete is a separate lifecycle.

## Consequences

- Teachers work in one coherent place without learning graph mechanics.
- Typed editing and version lineage apply beyond slide decks to every artifact surface.
- AI assistance remains teacher-confirmed and structurally bounded.
- Dependency and export staleness become visible rather than surprising.
- Collaboration is useful enough for delegated review without introducing real-time editing infrastructure.

## Considered Options

- **Stage wizard as the primary product**: rejected because it fragments continuing review and editing work.
- **Chat-first product**: rejected because artifact comparison, versions, quality, and structured editing need a stable canvas.
- **Freeform WYSIWYG**: rejected because it breaks typed contracts and deterministic rendering.
- **Raw JSON editor**: rejected because it exposes implementation shapes and weakens safety.
- **Autosave every content keystroke**: rejected because immutable version history would become noisy.
- **Automatic dependent regeneration**: rejected because it silently changes teacher-approved content.

## References

- ADR-023 Artifact UI Layer from Template Corpus
- ADR-025 Renderer Artifact-Kind Plugin Registry Rewrite
- ADR-042 Slide Deck Surfaces, Quality Gates, and Release Evidence
- ADR-047 Slide Deck In-Browser Editor and AI-Assisted Revision
- ADR-052 ArtifactDocument, Stable Identity, Answer Separation, and Variants
