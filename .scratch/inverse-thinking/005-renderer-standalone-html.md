---
title: Render Inverse Thinking artifacts as standalone HTML
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Add renderer support for projected inverse-thinking components so lesson, worksheet, quiz, and drill artifacts can render as standalone, print-ready, mobile-friendly HTML with strong creative frames inspired by the provided templates.

The renderer must not own pedagogy. It should map projected components into presentational components and frame styles while preserving no-CDN, answer-key separation, and accessibility requirements.

## Acceptance criteria

- [ ] Renderer supports inverse-thinking component variants such as case flow, evidence card, clue chips, safe zone, filing note, summary table, student challenge, and teacher-only key.
- [ ] Built-in creative frames can render at least `detective_case` and a neutral fallback without changing core schema.
- [ ] Frame styling is standalone: no Google Fonts, no CDN, no external images, and no external scripts.
- [ ] Rendered HTML includes required brand/standalone invariants and print styles.
- [ ] Student-facing HTML does not contain teacher-only answers or rationales in parseable visible content.
- [ ] Rendering tests cover lesson, worksheet, quiz, and drill projections from the same canonical pack.
- [ ] Tests assert no `http://` or `https://` asset references appear in rendered output.
- [ ] Tests include mobile/print-safe structural checks for the case-file layout and summary table.

## Detailed test suite

- [ ] `packages/renderer/__tests__/inverse-thinking-render.test.ts`: Given lesson, worksheet, quiz, and drill projections, when rendered, then each output contains `<!DOCTYPE html>`, `oh-my-class`, viewport meta, print styles, and no external assets.
- [ ] `packages/renderer/__tests__/inverse-thinking-teacher-only.test.ts`: Given teacher-only answer/rationale fields, when student HTML renders, then teacher-only content is absent from visible student DOM and only appears in teacher-only output.
- [ ] `packages/renderer/__tests__/inverse-thinking-frames.test.ts`: Given `detective_case` and neutral fallback frames, when rendered, then semantic components remain identical while frame classes/tokens differ.
- [ ] `packages/renderer/__tests__/inverse-thinking-responsive.test.ts`: Given the rendered case flow and summary table, when inspected at 375/768/1280/1920 structural breakpoints, then navigation, table overflow, and print page breaks remain usable.
- [ ] `packages/renderer/__tests__/standalone-assets.test.ts`: Assert zero `http://`, `https://`, external `<link>`, external `<script>`, Google Fonts, or CDN references.
- [ ] Visual QA fixture: include a golden HTML fixture based on `docs/templates/inverse-thinking-template.html`, adapted to offline-safe fonts/assets.
- [ ] Run `pnpm --filter @oh-my-class/renderer test` or the package's equivalent Vitest command; if missing, add renderer Vitest config first.

## Blocked by

- .scratch/inverse-thinking/001-contracts-and-canonical-pack.md
- .scratch/inverse-thinking/002-methodology-package-and-projections.md
