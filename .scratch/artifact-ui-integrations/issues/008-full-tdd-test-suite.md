---
title: Full TDD test suite for Artifact UI
status: ready-for-agent
labels: [renderer, testing, tdd]
created: 2026-07-02
---

## Parent

ADR-024: Artifact UI Renderer Integration

## What to build

Comprehensive test suite covering all Artifact UI invariants. Tests are written TDD-style (RED → GREEN) and cover CSS contract compliance, standalone HTML invariants, teacher/student projection safety, and contract adapter correctness.

This issue consolidates test files created by issues 001-007 into a coherent, complete test suite. Any gaps found during integration are filled here.

## Test categories

### 1. CSS Contract Tests (`css-contract.test.ts`)
- All CSS files have zero external URLs
- `contract.css` defines all required semantic tokens
- Each family token file overrides contract tokens
- No `--color-*` references in Artifact UI CSS (namespace isolation)
- All `art-*` classes are prefixed correctly

### 2. Standalone HTML Tests (`standalone-html.test.ts`)
- Every rendered output starts with `<!DOCTYPE html>`
- Every rendered output contains `<meta charset="UTF-8">`
- Every rendered output contains `<meta name="viewport">`
- Every rendered output contains `oh-my-class` brand string
- Every rendered output contains `data-artifact-theme="{family}"`
- No rendered output contains `http://` or `https://` in href/src attributes
- No rendered output contains `<link rel="stylesheet">`
- No rendered output contains `<script src="http`
- No rendered output contains `@import url(http`

### 3. Teacher/Student Projection Safety Tests (`projection-safety.test.ts`)
- Navy-ticket teacher teaching contains `art-projection-flag`
- Navy-ticket student teaching contains zero `art-projection-flag`
- Navy-ticket student teaching contains zero `art-teacher-block`
- Navy-ticket teacher practice contains answer + rationale
- Navy-ticket student practice contains zero answer + rationale
- Investigation-folder student contains zero `teacher_only` fields
- All student outputs pass grep for teacher-only strings: `Kịch bản giảng`, `class="art-pq-ans"`, `Đáp án:`, `Cambridge Dictionary`

### 4. Family Isolation Tests (`family-isolation.test.ts`)
- Rendering with navy-ticket does not produce `paper-dossier` selectors
- Rendering with paper-dossier does not produce `navy-ticket` selectors
- Each family's CSS is self-contained (no cross-family dependencies)

### 5. Print Safety Tests (`print-safety.test.ts`)
- All rendered output contains `@media print` rules
- Print rules hide `.art-print-btn` and `.art-no-print`
- Print rules set `background: white` on `.art-root`

## Acceptance criteria

- [ ] All test files exist under `packages/renderer/__tests__/artifact-ui/`
- [ ] All tests are RED before implementation (TDD)
- [ ] All tests are GREEN after implementation
- [ ] Test coverage for `src/artifact-ui/` is ≥ 90%
- [ ] No test uses mocks for CSS content (real CSS files are tested)
- [ ] No test uses mocks for contract data (real contract shapes are tested)

## Detailed test suite

See test categories above. Each category has 5-10 test cases = ~30-50 total test cases.

## Verification

- `pnpm --filter @oh-my-class/renderer test -- --testPathPattern=artifact-ui` → all tests pass
- `pnpm --filter @oh-my-class/renderer test -- --coverage --testPathPattern=artifact-ui` → coverage ≥ 90%
- Manual: run tests in watch mode, modify a CSS file, verify relevant tests fail (RED)

## Blocked by

- `001` through `007` — all implementation must be complete before final test consolidation
- Tests for individual issues are written alongside implementation (TDD); this issue fills gaps
