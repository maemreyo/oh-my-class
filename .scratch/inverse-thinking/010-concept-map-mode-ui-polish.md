---
title: Concept Map mode UI polish and component gap closure
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Polish `concept_map` as a first-class methodology mode. The quality gate currently accepts `vocab_cluster` or `contrastive_pairs` for this tag, but exploration found no dedicated `vocab_cluster` template. This issue must make the mode visible to teachers and close or explicitly resolve that component ambiguity.

## Acceptance criteria

- [ ] The teacher mode inspector explains that Concept Map requires a vocabulary cluster or contrastive-pair structure.
- [ ] The renderer supports the chosen valid component path for Concept Map; if `vocab_cluster` remains accepted by the gate, a `vocab_cluster` renderer component exists.
- [ ] Concept Map preview emphasizes relationships, grouping, and student navigation rather than generic cards.
- [ ] Teacher UI shows missing required component warnings when `concept_map` is declared but no valid component projection exists.
- [ ] Design supports dense concept maps on mobile without clipping labels or losing relationship meaning.

## Detailed test suite

- [ ] `packages/quality` test: Given `methodology_tags=["concept_map"]` and no `vocab_cluster`/`contrastive_pairs`, when methodology gate runs, then it fails with a clear missing-component message.
- [ ] Renderer test: Given a valid Concept Map projection, when rendered, then all nodes/groups/links are present, no external assets are used, and print layout remains readable.
- [ ] UI inspector test: Given the missing-component failure, when the inspector renders, then it names Concept Map and the accepted component alternatives.
- [ ] Responsive visual test: Render a dense Concept Map at 375 and 1280px and assert no clipped core labels.
- [ ] Accessibility test: Concept groups and relationships have text alternatives or descriptive labels for screen readers.
- [ ] Regression test: `contrastive_pairs` remains a valid path for `concept_map` when that projection is used.

## Blocked by

- .scratch/inverse-thinking/008-system-wide-mode-ui-polish.md
