---
title: Wire vocabulary batch exporter to renderArtifactUi()
status: ready-for-agent
labels: [exporters, renderer, wiring, vocabulary]
created: 2026-07-02
---

## Parent

ADR-024: Artifact UI Renderer Integration

## What to build

Update the vocabulary batch exporter to use `renderArtifactUi()` instead of `renderSemanticAnchorProjectionSet()`. This is a cross-package change: `packages/exporters/src/vocabulary-batch/index.ts` imports from `@oh-my-class/renderer`.

## Current state

`packages/exporters/src/vocabulary-batch/index.ts:172`:
```typescript
const projections = renderSemanticAnchorProjectionSet(cluster, input.practiceSet);
```

This calls the old inline renderer which produces HTML with hardcoded CSS. After migration, it should call the new Artifact UI renderer which produces HTML with `art-*` classes and `data-artifact-theme="navy-ticket"`.

## Target state

```typescript
import { renderArtifactUi } from "@oh-my-class/renderer";

// For each cluster:
const teachingTeacher = await renderArtifactUi({
  family: 'navy-ticket',
  contract: cluster,
  audience: 'teacher',
  kind: 'teaching',
  artifactType: 'vocabulary_batch',
});
// ... repeat for teachingStudent, practiceTeacher, practiceStudent
```

Or, if `renderArtifactUi` provides a convenience wrapper:
```typescript
const projections = await renderArtifactUiSet({
  family: 'navy-ticket',
  cluster,
  practiceSet,
});
```

## Acceptance criteria

- [ ] `packages/exporters/src/vocabulary-batch/index.ts` imports `renderArtifactUi` (or convenience wrapper) from `@oh-my-class/renderer`
- [ ] `renderSemanticAnchorProjectionSet` import is removed
- [ ] Exported HTML files have `data-artifact-theme="navy-ticket"` on root element
- [ ] Exported HTML files use `art-*` CSS classes (not inline styles)
- [ ] Teacher projection files contain `art-projection-flag` markers
- [ ] Student projection files contain zero `art-teacher-block` elements
- [ ] Export manifest still lists all 4 HTML files per cluster (teaching teacher/student, practice teacher/student)
- [ ] GIFT and H5P exports are unchanged (they don't consume HTML)
- [ ] Existing exporter tests still pass

## Detailed test suite

- [ ] `packages/exporters/__tests__/vocabulary-batch.test.ts` (existing): all tests still pass
- [ ] `packages/exporters/__tests__/vocabulary-batch-artifact-ui.test.ts`: exported HTML contains `data-artifact-theme="navy-ticket"`
- [ ] `packages/exporters/__tests__/vocabulary-batch-artifact-ui.test.ts`: exported student HTML contains zero `art-teacher-block`
- [ ] `packages/exporters/__tests__/vocabulary-batch-artifact-ui.test.ts`: exported HTML contains `oh-my-class` brand string
- [ ] `packages/exporters/__tests__/vocabulary-batch-artifact-ui.test.ts`: manifest still lists 4 HTML files per passed cluster

## Verification

- `pnpm --filter @oh-my-class/exporters test` → all tests pass
- Manual: export a vocabulary batch, open HTML files in browser, verify Artifact UI styling
- Manual: `grep "data-artifact-theme" dist/clusters/*/teaching-teacher.html` → matches for all clusters

## Blocked by

- `007-public-api-render-artifact-ui.md` — renderArtifactUi() must exist
- `005-replace-semantic-anchor-renderer.md` — navy-ticket family must be wired
