# ADR-030: Full Artifact-Type and Export Coverage

## Status

**Proposed** (2026-07-03) — Teachers can only request a subset of artifact types over the API (`lesson, worksheet, quiz, drill, recap, infographic`), even though the renderer already ships plugins for `flashcard_deck`, `answer_key`, and `roadmap`. This ADR closes the gap so every renderable output type is requestable end-to-end and its export formats are produced. Accepts and supersedes the "Proposed" status of ADR-024 (flashcard export). Companion to ADR-028/029; enables the teacher-scenario driver to demonstrate every output type.

## Context

Verified against code (2026-07-03):
- **Renderers already exist** for the missing types: `packages/renderer/src/plugins/{flashcard-deck,answer-key,roadmap}.ts` + `contracts/*` + `sanitizer/configs/*`. So rendering is NOT the gap.
- **Contract gate excludes them.** The requestable set validated at contract setup rejects any type outside `{lesson, worksheet, quiz, drill, recap, infographic}` by opening a `clarification_required` gate. `flashcard_deck` is in the `ArtifactType` Literal (`common/contracts/run_contract.py:11`) but **not** in the supported set; `answer_key` and `roadmap` are **not even in the Literal**.
- **Export.** `flashcard_tsv`/`anki_apkg` are in `SUPPORTED_EXPORTS` and the `ExportFormat` Literal, but the flashcard export wiring is only "Proposed" (ADR-024); the writer shells out to the Node CLI `packages/exporters/dist/cli.js` (built) and fails closed if absent.
- **Safety.** `answer_key` content must remain teacher-only — INVARIANT-05 (answer keys in `teacher_only` sections; the compliance gate blocks answer-key leakage into student HTML).

## Decision

### 1. Make all renderable types requestable

- Add `answer_key` and `roadmap` to the `ArtifactType` Literal (`run_contract.py`) and the generated TS/Zod schema; regenerate schemas (`make gen-schemas`).
- Add `flashcard_deck`, `answer_key`, `roadmap` to the supported/validation set used at contract setup so they no longer trip `clarification_required`.

### 2. Wire content generation for the new types

Ensure `content_creator` has the prompt contract + `ARTIFACT_RICHNESS` entries and RCM component contracts for `flashcard_deck`, `answer_key`, `roadmap`, producing `ArtifactContent` that the existing renderer plugins accept. Each type gets schema/round-trip contract tests.

### 3. Accept ADR-024 flashcard export

Move ADR-024 (Quizlet/Anki/`flashcard_tsv`) from Proposed → Accepted and wire it: when `export_formats` includes `flashcard_tsv`/`anki_apkg` and a `flashcard_deck` artifact exists, produce those files via the built Node CLI; fail-closed with a clear error if the CLI is unbuilt (build step documented + in CI).

### 4. Safety: answer_key is teacher-only

`answer_key` is generated into `teacher_only` sections and must never appear in the student preview/export. The compliance gate (ADR-026 dependency) already blocks answer-key leakage; add explicit per-type tests: student view of an `answer_key`-bearing pack contains no answer markers, teacher view does. This is an INVARIANT-05 extension, not a relaxation.

### 5. Fan-out dependency review

Slot the new types into the artifact fan-out dependency graph appropriately (e.g. `answer_key` depends on the assessment artifacts it keys; `roadmap`/`flashcard_deck` depend on `lesson`). Update the wave definitions so scoped-replan (agents-hardening #27) reasons about them correctly.

## Consequences

- Every renderer-supported output type becomes end-to-end requestable, generatable, reviewable at the teacher gate, and exportable — the teacher-scenario driver can demonstrate all of them.
- Reuses existing renderer plugins — low rendering risk; the work is contract + generation + export + tests.
- `answer_key` widens the answer-key-leakage surface → INVARIANT-05 tests must expand in lockstep (fail-closed).
- Schema change (`ArtifactType` Literal) is cross-language → Pydantic + Zod parity check (`make check-schemas`) must pass.
- ADR-024 becomes Accepted; the Node exporter CLI build becomes a required step for flashcard exports.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| **Enable all three + accept ADR-024 (chosen)** | Full coverage; renderers already exist; demonstrable | Widens answer-key safety surface; schema + export wiring work |
| Enable `flashcard_deck` only | Smallest step; matches immediate demo need | Leaves `answer_key`/`roadmap` renderers unused; partial coverage |
| Leave as-is, document unsupported | Zero work | "Cover all output types" goal unmet; shipped renderers stay dead |
