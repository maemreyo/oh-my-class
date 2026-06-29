---
title: Film Based mode UI polish and film_clip_activity gap closure
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Make `film_based` a usable and polished mode. The quality gate requires `film_clip_activity`, but exploration found a renderer-side `film_card` naming mismatch instead. This issue must resolve the gap so film-based lessons can pass gates and render consistently without external media dependencies.

## Acceptance criteria

- [ ] The gate-required `film_clip_activity` component type has a renderer path, or the gate/registry is intentionally aligned to the existing component type with tests.
- [ ] Film-based UI supports clip context, pre-watch prompt, while-watch task, post-watch reflection, and offline-safe fallback text.
- [ ] No external video, CDN, thumbnail, or script is required for standalone HTML export.
- [ ] Teacher preview clearly distinguishes what happens before, during, and after the clip.
- [ ] If a video URL is teacher-provided, exported standalone HTML records it as text/reference only unless a future offline media pipeline exists.

## Detailed test suite

- [ ] Quality test: Given `methodology_tags=["film_based"]` and no valid film activity component, when the methodology gate runs, then it fails with the required type named.
- [ ] Renderer test: Given a valid film activity projection, when rendered, then pre/during/post sections appear, no external assets are loaded, and print view remains useful.
- [ ] Standalone test: Assert rendered film-based HTML contains no `iframe`, external `<video src>`, CDN, or remote thumbnail by default.
- [ ] UI inspector test: Given film-based methodology status, when rendered, then it shows clip context and required component satisfaction.
- [ ] Visual QA: Capture the film activity card at mobile/tablet/desktop with long Vietnamese prompts.
- [ ] Naming regression: Test that gate-required component type and renderer-supported component type stay aligned.

## Blocked by

- .scratch/inverse-thinking/008-system-wide-mode-ui-polish.md
