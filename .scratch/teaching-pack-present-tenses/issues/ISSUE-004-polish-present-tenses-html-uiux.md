---
title: Polish Present Tenses rendered HTML UI and readability
status: completed
labels: [ready-for-agent, teaching-pack, present-tenses, ui-ux, visual-qa]
created: 2026-06-29
order: 4
blocked_by: [ISSUE-001-real-system-generated-present-tenses-pack, ISSUE-003-deepen-inverse-thinking-scaffolding]
---

## What to build

Improve the rendered Present Tenses HTML so it is easy to scan and usable as a classroom teaching pack. This slice focuses on hierarchy, spacing, visual distinction between component types, and responsive readability without weakening the standalone HTML invariants.

## Acceptance criteria

- [x] H2/H3 hierarchy is visibly distinct enough that section boundaries are clear at desktop and mobile widths.
- [x] Trap scenario, rule summary, practice, and teacher note components have visually distinct treatments.
- [x] Within-section component spacing gives enough breathing room for long Vietnamese/English mixed text.
- [x] The four-column thinking table is readable at mobile-ish width or degrades into a usable layout.
- [x] Browser QA covers at least desktop `1280px` and mobile `375px` screenshots.
- [x] Visual QA records concrete findings and a final verdict; any remaining readability gaps are documented.
- [x] Standalone HTML invariants still pass: no external assets, brand present, no student answer-key leakage.

## Progress notes

- Fixed the active preview storage seam so newly created student previews use renderer-produced HTML with teacher-only sections removed, instead of flattening `content_json` into primitive text-only sections.
- Regression test: `test_student_preview_preserves_rendered_snapshot_markup` verifies component markup like `class="lesson-card"` survives the public preview endpoint while answer-key content is removed.
- This is a system-level UI/UX prerequisite, not full visual polish. Existing completed Present Tenses snapshots were persisted before the fix and remain primitive; a fresh run or snapshot regeneration is still needed before final browser visual QA.
- Fresh post-fix browser QA used run `cf1bf05f-dbf5-48bd-858a-2956c59dbb49` lesson export.
- Desktop screenshot: `.scratch/teaching-pack-present-tenses/artifacts/browser-qa/cf1bf05f-dbf5-48bd-858a-2956c59dbb49/lesson-desktop-1280.png`.
- Mobile screenshot: `.scratch/teaching-pack-present-tenses/artifacts/browser-qa/cf1bf05f-dbf5-48bd-858a-2956c59dbb49/lesson-mobile-375.png`.
- Objective Playwright layout checks:
  - Desktop `1280x900`: `horizontalOverflow=false`, `h1Count=1`, `h2Count=17`, `h3Count=1`, `sectionCount=7`, `tableCount=2`, table widths `1188px` inside `1280px` viewport.
  - Mobile `375x812`: `horizontalOverflow=false`, `h1Count=1`, `h2Count=17`, `h3Count=1`, `sectionCount=7`, `tableCount=2`, table widths `339px` inside `375px` viewport.
- Remaining readability note: hierarchy is functional, but generated H2 font sizes vary (`19.5px` and `23.25px`) because component headings and section headings render with different styles. Acceptable for this slice, but worth smoothing in a future design-system pass.

## Blocked by

- ISSUE-001-real-system-generated-present-tenses-pack
- ISSUE-003-deepen-inverse-thinking-scaffolding
