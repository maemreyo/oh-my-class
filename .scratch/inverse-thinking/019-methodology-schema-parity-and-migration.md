---
title: Methodology schema parity and migration across Pydantic and Zod
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Close the schema parity gap discovered in the codebase: `common/contracts/lesson_plan.py` defines typed `MethodologyMetadata` and `MethodologyTag`, but generated TypeScript currently exposes `methodology: z.any()`, while the deprecated handwritten `common/schemas/src/lesson_plan.ts` omits `methodology` entirely. This weakens teacher UI typing and makes mode-picker/inspector work vulnerable to drift.

This slice should make Pydantic the single source of truth and remove or quarantine the handwritten schema path so all frontend and renderer code consumes generated methodology types.

## Acceptance criteria

- [ ] Generated Zod schema for `LessonPlan` includes typed `MethodologyMetadata`, not `z.any()`.
- [ ] Generated schema includes the complete supported tag union, including `inverse_thinking` after issue 001 lands.
- [ ] The deprecated handwritten `common/schemas/src/lesson_plan.ts` is removed, redirected, or made an explicit compatibility shim that imports from generated schema.
- [ ] Frontend and renderer imports use generated schemas/types only.
- [ ] `make check-schemas` catches any mismatch between Pydantic and Zod methodology fields.
- [ ] No `methodology` field is accepted as arbitrary JSON past the schema boundary.

## Detailed test suite

- [ ] `common/contracts/tests/test_lesson_plan.py`: Given valid methodology tags, when `LessonPlan` parses, then `MethodologyMetadata.tags` preserves the exact typed tag list.
- [ ] `common/contracts/tests/test_lesson_plan.py`: Given an unknown tag, when parsed, then Pydantic raises a validation error.
- [ ] Schema generation test: Given generated `common/schemas/src/generated/lesson_plan.ts`, when inspected, then `methodology` is a typed object schema with `tags` as an enum array, not `z.any()`.
- [ ] TypeScript test: Given the generated type, when assigning an invalid methodology tag, then `tsc --noEmit` fails without `as any` or suppressions.
- [ ] Migration test: Existing fixtures with `methodology: null` and omitted methodology remain valid.
- [ ] Run `python scripts/generate_zod_schemas.py`, `pnpm verify:schemas`, and `pnpm exec tsc --noEmit`.

## Blocked by

- .scratch/inverse-thinking/001-contracts-and-canonical-pack.md
