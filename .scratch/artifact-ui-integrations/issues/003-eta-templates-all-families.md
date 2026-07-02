---
title: Eta templates for all artifact UI families + interactivity
status: ready-for-agent
labels: [renderer, eta, templates, interactivity]
created: 2026-07-02
---

## Parent

ADR-024: Artifact UI Renderer Integration

## What to build

Create Eta templates for all artifact UI families plus the root-cause session dossier. Each template uses Artifact UI CSS classes (`art-*`) and renders standalone HTML with inlined CSS. Templates are self-contained — they do NOT include `base.html` (Artifact UI has its own shell via `.art-root` + `data-artifact-theme`).

**Interactivity:** Templates that use reveal/toggle/jump contracts (answer-key, root-cause-session) must inline `interactivity.js` in a `<script>` block inside `<head>` (NOT `<body>`). Placing the script in `<head>` ensures it is never processed by `sanitizeArtifactUi()`, which only sanitizes body content. The JS is vanilla-only, no eval, no remote src (Issue 014 verifies this).

Source HTML shapes from `.scratch/artifact-ui-integrations/resources/artifact-ui/pages/*.js` provide the exact HTML structure. Port those string-building patterns into Eta `.html` templates.

## Template inventory

### navy-ticket (vocabulary)
- `templates/artifact/navy-ticket/teaching.teacher.html` — Teacher projection with scripts, sources, edge cases
- `templates/artifact/navy-ticket/teaching.student.html` — Student projection without teacher-only content
- `templates/artifact/navy-ticket/practice.teacher.html` — Practice with answers + rationale
- `templates/artifact/navy-ticket/practice.student.html` — Practice without answers

### paper-dossier (lesson/key/root-cause)
- `templates/artifact/paper-dossier/lesson.html` — Lesson/path dossier with sidebar, objectives, concept boxes, roleplay
- `templates/artifact/paper-dossier/answer-key.html` — Exam answer key with question grid, option states, explanations, **interactivity.js inlined**
- `templates/artifact/paper-dossier/root-cause-session.html` — Root-cause/Socratic session dossier with anchor timeline, controlled comparison, generalization checkpoint, **interactivity.js inlined**

### transit-route (video)
- `templates/artifact/transit-route/video-route.html` — Video learning route with ticket header, station cards, timeline

### investigation-folder (inverse-thinking)
- `templates/artifact/investigation-folder/inverse-thinking.html` — Investigation dossier with case cards, process strips, evidence

## Interactivity contracts (shared across templates)

Templates that use reveal/toggle/jump must inline `interactivity.js` and use these data-* attributes:

| Contract | Attributes | Used by templates |
|----------|-----------|-------------------|
| 1 — reveal/toggle | `data-toggle-reveal`, `aria-controls`, `aria-expanded`, `data-hide-after-reveal`, `data-toggle-group` | answer-key, root-cause-session |
| 2 — mode toggle | `data-mode-toggle`, `data-toggles-group`, `role="switch"` | answer-key |
| 3 — jump-to-target | `data-jump-input-el`, `data-jump-go`, `data-jump-to` | answer-key |

## Acceptance criteria

- [ ] All 9 templates exist at the correct paths under `packages/renderer/templates/artifact/`
- [ ] Each template is a valid Eta template (uses `<%= %>` for data access, `<%~ %>` for unescaped output)
- [ ] Each template wraps content in `<div class="art-root" data-artifact-theme="{family}">`
- [ ] Each template receives `artifactCSS` and inlines it in a `<style>` block
- [ ] Each template includes the `oh-my-class` brand string in footer or header
- [ ] Teacher projections include `art-projection-flag` and `art-teacher-block` markers
- [ ] Student projections contain zero teacher-only DOM (no `art-teacher-block`, no `art-projection-flag`)
- [ ] All templates produce valid HTML5 (DOCTYPE, html, head, body)
- [ ] No `http://` or `https://` in any template (except data-bound URLs passed by adapter)
- [ ] Print styles (`@media print`) hide interactive-only chrome (print button, theme switcher)
- [ ] Templates use `art-*` CSS classes exclusively (no inline `style=` attributes)
- [ ] answer-key and root-cause-session templates inline `interactivity.js` in `<script>` block
- [ ] `interactivity.js` content is verbatim from `resources/artifact-ui/interactivity.js` (no modifications)
- [ ] Root-cause session template uses new primitives: art-anchor-timeline, art-controlled-comparison, art-scenario-anchor, art-generalization-checkpoint, art-stress-test, art-metaphor-log

## Detailed test suite

- [ ] `packages/renderer/__tests__/artifact-ui/templates.test.ts`: renders each template with mock data → produces valid HTML
- [ ] `packages/renderer/__tests__/artifact-ui/templates.test.ts`: rendered HTML contains `data-artifact-theme="{family}"`
- [ ] `packages/renderer/__tests__/artifact-ui/templates.test.ts`: rendered HTML contains `oh-my-class` brand string
- [ ] `packages/renderer/__tests__/artifact-ui/templates.test.ts`: student template output contains zero `art-teacher-block` or `art-projection-flag` elements
- [ ] `packages/renderer/__tests__/artifact-ui/templates.test.ts`: rendered HTML contains no `http://` or `https://` in href/src attributes
- [ ] `packages/renderer/__tests__/artifact-ui/templates.test.ts`: rendered HTML starts with `<!DOCTYPE html>`
- [ ] `packages/renderer/__tests__/artifact-ui/templates.test.ts`: answer-key template output contains `<script>` block with interactivity.js content
- [ ] `packages/renderer/__tests__/artifact-ui/templates.test.ts`: root-cause-session template output contains `<script>` block with interactivity.js content
- [ ] `packages/renderer/__tests__/artifact-ui/templates.test.ts`: root-cause-session template output contains `art-anchor-timeline` class
- [ ] `packages/renderer/__tests__/artifact-ui/templates.test.ts`: root-cause-session template output contains `art-generalization-checkpoint` class
- [ ] `packages/renderer/__tests__/artifact-ui/templates.test.ts`: rendered HTML contains no `eval(` in script blocks

## Verification

- `pnpm --filter @oh-my-class/renderer test -- --testPathPattern=artifact-ui` → all tests pass
- Manual: render each template with mock data, save to `/tmp/`, open in browser — visual inspection
- Manual: `grep -c "http://" templates/artifact/**/*.html` → zero matches per file

## Blocked by

- `002-family-registry-and-css-loader.md` — templates need `artifactCSS` from the loader
- `015-root-cause-session-contract.md` — `root-cause-session.html` template must bind against `RootCauseSessionData` shape; review the contract before writing the template
- `017-investigation-folder-frame-variants.md` — read before writing `inverse-thinking.html`; the template uses `it.frameVariant` for CSS modifier classes
