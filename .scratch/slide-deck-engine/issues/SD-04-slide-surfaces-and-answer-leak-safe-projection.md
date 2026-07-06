---
title: Render student, teacher, and print slide_deck surfaces with leak-safe projection
status: done
labels: [slide-deck-engine, renderer, compliance, ready-for-agent]
created: 2026-07-06
---

## Parent

ADR-042.

## What to build

Extend the minimal `slide_deck` tracer into the three required production surfaces from one canonical `SlideDeckData`: student presentation HTML, teacher guide/preview HTML, and print HTML. The renderer must project each surface explicitly and fail closed if student-facing output contains teacher-only or answer-bearing data.

Student presentation is for classroom display: no speaker notes, no answer keys, no teacher-only slides or blocks, no hidden answer payloads. Teacher guide includes facilitation notes, pacing, misconceptions, and answer guidance. Print HTML expands or preserves reveal content in a print-safe way with page breaks.

## Acceptance criteria

- [x] Renderer can produce student presentation, teacher guide, and print surfaces from the same fixture deck.
- [x] Student surface strips teacher-only slides, blocks, speaker notes, facilitation notes, answer keys, correct answers, explanations intended for teachers, and hidden answer JSON.
- [x] Teacher surface includes facilitation notes and answer guidance in a teacher-only panel or section.
- [x] Print surface includes page breaks, readable all-visible content, and no interactive-only dead ends.
- [x] Compliance tests fail when answer-bearing or teacher-only data appears in student-facing HTML.
- [x] Snapshot/export tests record which surface was rendered and include render manifests/diagnostics where the renderer supports them.

## Todo items

- [x] Add explicit projection adapters for student presentation, teacher guide, and print surfaces.
- [x] Add student-surface stripping for teacher-only slides, blocks, notes, answer data, and hidden payloads.
- [x] Add teacher-surface rendering for facilitation notes, pacing, misconceptions, and answer guidance.
- [x] Add print-surface rendering with page breaks and reveal-expanded content.
- [x] Add rendered-HTML compliance tests for answer/teacher-only leakage.
- [x] Update snapshot/export diagnostics to record rendered surface metadata.

## Completion notes

- Added explicit `student`, `teacher`, and `print` slide-deck projections before Eta rendering.
- Student rendering strips teacher notes and answer metadata, then fails closed if projected teacher-only text appears in the rendered HTML.
- Teacher rendering shows facilitation notes, answer guidance, and correct-option markers; print rendering expands reveal policy and includes page-break CSS.
- Focused verification passed: `pnpm --dir packages/renderer exec vitest run __tests__/slide-deck-renderer.test.ts`, with clean LSP diagnostics on changed renderer files.

## Blocked by

- SD-03 minimal slide_deck tracer through pipeline.

## References

- `docs/adr/042-slide-deck-surfaces-quality-and-release-gates.md`
- `packages/quality/compliance_policy.py`
- `services/gateway/renderer_adapter.py`
- `packages/renderer/src/sanitizer/`
- `packages/renderer/templates/pages/`

## Implementation notes

- Prefer separate projection/adaptation functions per surface over one template full of mode conditionals.
- Student safety must be tested at rendered HTML level, not just source data level.
- Do not serialize correct answers into client-side data attributes or scripts for student presentation.
