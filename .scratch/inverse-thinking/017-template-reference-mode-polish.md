---
title: Template reference mode polish for key, path, learning-vocab, and learning-via-video
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Turn the raw reference templates in `docs/templates/` into production-ready mode design references without copying their CDN/external-asset assumptions. Exploration found five raw special-mode HTML references: `key-template.html`, `learning-via-video-template.html`, `inverse-thinking-template.html`, `path-template.html`, and `learning-vocab-template.html`. Inverse Thinking is handled by dedicated issues; this issue covers the remaining reference modes as design contracts to be adapted into standalone, tokenized renderer/dashboard surfaces.

## Acceptance criteria

- [ ] Inventory `docs/templates/key-template.html`, `learning-via-video-template.html`, `path-template.html`, and `learning-vocab-template.html` into documented mode design briefs.
- [ ] For each reference mode, identify reusable primitives, teacher-facing controls, renderer components, and quality-gate expectations.
- [ ] Strip or replace external asset assumptions such as Google Fonts/CDNs with theme tokens and offline-safe system assets.
- [ ] Add issue-ready follow-up slices if any reference mode requires a full new methodology contract rather than renderer-only polish.
- [ ] Ensure these modes integrate with the shared mode picker/preview shell from the system-wide UI issue.

## Detailed test suite

- [ ] Documentation test/check: Given each reference template, when the inventory script/check runs, then every file has a corresponding design brief entry with primitives, controls, renderer surfaces, and test expectations.
- [ ] Standalone adaptation tests: For each adapted reference fixture, assert no `http://`, `https://`, Google Fonts, CDN links, external scripts, or remote images remain.
- [ ] Renderer fixture tests: Render one minimal fixture per reference mode and assert DOCTYPE, brand string, viewport meta, print styles, and theme token usage.
- [ ] Visual QA: Capture key/path/vocab/video reference fixtures at 375/768/1280px and verify no major clipping or unreadable dense sections.
- [ ] UI integration test: Given the shared mode picker, when a reference mode is available, then its description, preview entry point, and disabled/coming-soon state render correctly.
- [ ] Follow-up completeness check: If a reference mode is marked not implementation-ready, then a new `.scratch` issue exists or the blocker is documented in this issue.

## Blocked by

- .scratch/inverse-thinking/008-system-wide-mode-ui-polish.md
