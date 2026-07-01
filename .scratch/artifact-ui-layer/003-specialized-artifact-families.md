---
title: Add specialized Artifact UI families for lesson, key, video, and inverse-thinking outputs
status: ready-for-agent
labels: []
created: 2026-07-01
---

## Parent

ADR-023: Artifact UI Layer from Template Corpus

## What to build

Extend the Artifact UI layer beyond semantic vocabulary by adding specialized component families derived from the remaining template corpus:

- lesson/path dossier from `learning-vocab-template.html` and `path-template.html`;
- exam answer-key from `key-template.html`;
- video learning route from `learning-via-video-template.html`;
- inverse-thinking investigation dossier from `inverse-thinking-template.html`.

This slice should make each family demoable through the component showcase and ready for future renderer integration. It should not force all existing artifact types to migrate in one change unless their contract/view model is already ready.

## Acceptance criteria

- [ ] Lesson/path dossier family includes sidebar, stat grid, objective card, concept box, table/comparison, roleplay script, and homework list primitives.
- [ ] Exam answer-key family includes question grid, answer-state card, option state, explanation block, and dense navigation primitives.
- [ ] Video-route family includes ticket header, mini route map, station card, timeline step, and offline-safe video placeholder wrapper.
- [ ] Inverse-thinking family includes folder cover, tabs, case card, process strip, stamp, and evidence block primitives.
- [ ] Showcase demonstrates each specialized family with realistic Vietnamese/English teaching content and no lorem ipsum.
- [ ] All family demos satisfy standalone HTML invariants: no external assets, no remote fonts, brand string present, print-safe styles where relevant.
- [ ] Responsive QA covers 375px, 768px, and 1280px for all specialized family demos.
- [ ] `DESIGN.md` documents the specialized families and when renderer/exporter code should choose each family.

## Blocked by

- `.scratch/artifact-ui-layer/001-core-artifact-design-system.md`
