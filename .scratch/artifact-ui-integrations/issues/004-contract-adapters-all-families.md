---
title: Contract adapters for all 4 families
status: ready-for-agent
labels: [renderer, contracts, adapters]
created: 2026-07-02
---

## Parent

ADR-024: Artifact UI Renderer Integration

## What to build

Create TypeScript adapter functions that transform typed contracts into Eta template data. Each family has one adapter that knows how to extract and reshape its specific contract type into the data shape the Eta template expects.

Adapters handle:
- Contract → template data transformation
- Teacher/student projection safety (ADR-022): adapters for student projections never receive teacher-only fields
- Default values for optional fields
- Escape HTML in user-provided strings

## Adapter inventory

### navy-ticket adapter (`adapters/navy-ticket.ts`)
- Input: `SemanticAnchorCluster` + `PracticeSet` (from `@oh-my-class/schemas`)
- Output: teaching/practice template data with `isTeacher` flag
- Must handle: teacher scripts, source notes, edge cases, answer rationale (teacher-only)

### paper-dossier adapter (`adapters/paper-dossier.ts`)
- Input: lesson plan data (from existing lesson contract)
- Output: lesson/answer-key template data
- Must handle: sidebar navigation, stat grid, objective cards, concept boxes, roleplay scripts

### transit-route adapter (`adapters/transit-route.ts`)
- Input: video route data (from existing video route contract)
- Output: video-route template data
- Must handle: station cards, timeline steps, video placeholder metadata

### investigation-folder adapter (`adapters/investigation-folder.ts`)
- Input: inverse-thinking data (from existing inverse-thinking contract)
- Output: inverse-thinking template data
- Must handle: case cards, process strips, evidence blocks, stamps

## Acceptance criteria

- [ ] Each adapter is a TypeScript function with explicit input/output types
- [ ] Each adapter handles teacher/student projection via `audience` parameter
- [ ] Student adapter output excludes: teacher_script_vi, source_notes, edge_cases, answer_key, rationale
- [ ] All user-provided strings are HTML-escaped by the adapter (not relying on template auto-escape)
- [ ] Adapters return a consistent data shape: `{ title, subtitle, lang, sections[], teacherOnly?, metadata? }`
- [ ] Each adapter is independently testable (pure function, no I/O)
- [ ] Adapters are exported from `src/artifact-ui/adapters/index.ts`
- [ ] No adapter imports from `apps/*` or `services/*` (ADR-024 boundary)

## Detailed test suite

- [ ] `packages/renderer/__tests__/artifact-ui/adapters/navy-ticket.test.ts`: teacher projection includes `teacher_script_vi` in output
- [ ] `packages/renderer/__tests__/artifact-ui/adapters/navy-ticket.test.ts`: student projection excludes `teacher_script_vi`, `source_notes`, `edge_cases`
- [ ] `packages/renderer/__tests__/artifact-ui/adapters/navy-ticket.test.ts`: HTML-escapes `<script>` in word field → `&lt;script&gt;`
- [ ] `packages/renderer/__tests__/artifact-ui/adapters/paper-dossier.test.ts`: transforms lesson plan sections into template data shape
- [ ] `packages/renderer/__tests__/artifact-ui/adapters/inverse-thinking.test.ts`: student projection excludes `teacher_only.rationale` and `teacher_only.answer_key`
- [ ] All adapter tests: output matches expected TypeScript interface (compile-time check)

## Verification

- `pnpm --filter @oh-my-class/renderer test -- --testPathPattern=artifact-ui/adapters` → all tests pass
- `pnpm --filter @oh-my-class/renderer typecheck` → no type errors
- Manual: import each adapter, call with mock contract data, inspect output shape

## Blocked by

- `001-port-css-foundation.md` — contracts must be importable (Zod schemas exist)
- `003-eta-templates-all-families.md` — adapter output shape must match template expectations (can be developed in parallel if data shape is agreed upfront)
