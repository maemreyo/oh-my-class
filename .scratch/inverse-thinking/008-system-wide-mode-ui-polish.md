---
title: System-wide methodology mode UI polish foundation
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Add the shared teacher-facing UI foundation for methodology modes before polishing individual modes. Today the contracts, renderer templates, and quality gates know about methodology tags, but the teacher dashboard has no mode-aware surface. This slice adds the reusable mode picker, methodology inspector, preview shell, and test infrastructure that every mode-specific issue can build on.

Grounding from exploration:

- `packages/quality/layer2_content/methodology.py` is the current tag-to-component gate for `concept_map`, `contrastive_pairs`, `film_based`, `shy_student_1on1`, `active_recall`, and `why_wrong_reasoning`.
- `apps/web` had no mode-tag matches in exploration, so this is greenfield teacher-facing UI.
- `apps/web/vitest.config.ts` exists; no repo-level Playwright config was found.
- `packages/renderer` needs mode preview integration but should not own pedagogy.

## Acceptance criteria

- [ ] Teacher-facing create/edit flow exposes a methodology mode picker with clear descriptions for Standard, Concept Map, Contrastive Pairs, Film Based, Shy Student 1:1, Active Recall, Why Wrong Reasoning, Timed Quiz, and Inverse Thinking.
- [ ] The picker uses generated/shared methodology tag data rather than duplicating string literals in UI code.
- [ ] Teacher Gate 1 and Teacher Gate 2 show methodology chips, selected mode rationale, and quality-gate status without bypassing human approval.
- [ ] A reusable methodology inspector can render declared tags, required components, satisfied/missing requirements, warning severity, and jump links into structured editor fields where available.
- [ ] A reusable preview shell renders standalone artifact HTML in a sandboxed iframe and supports desktop/tablet/mobile preview widths.
- [ ] UI design follows a tokenized design-system baseline: no hardcoded production hex values in component code, clear focus states, reduced-motion support, and accessible color contrast.
- [ ] The work does not implement any single mode's bespoke editor; it only provides shared surfaces for later issues.

## Detailed test suite

- [ ] `apps/web` Vitest component tests: Given methodology metadata, when the mode picker renders, then all supported modes appear with accessible labels, descriptions, and selected/disabled states.
- [ ] `apps/web` Vitest tests: Given quality-gate results, when the methodology inspector opens, then it groups pass/warning/fail statuses and exposes jump links without throwing on unknown future tags.
- [ ] `apps/web` Vitest tests: Given the preview shell, when HTML is supplied, then it renders in an iframe with a restrictive sandbox and never uses `allow-same-origin` together with scripts.
- [ ] Accessibility tests: Keyboard-only navigation reaches picker, inspector, preview controls, and gate actions; all errors/warnings are announced via `role="alert"` or `aria-live`.
- [ ] Visual QA tests: Capture mode picker, inspector, and preview shell at 375, 768, and 1280px; verify no clipped text for Vietnamese mode descriptions.
- [ ] Token guard: Add or use a grep/AST test that fails if production UI components introduce raw hex colors instead of tokens.
- [ ] Playwright infrastructure issue hook: If no repo-level Playwright config exists, add a documented TODO or prerequisite inside this issue's implementation plan before visual E2E assertions are marked complete.

## Blocked by

- .scratch/inverse-thinking/001-contracts-and-canonical-pack.md for typed inverse-thinking metadata
