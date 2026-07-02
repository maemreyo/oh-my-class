---
title: Wire agent-renderer.ts — lesson/answer_key → paper-dossier
status: ready-for-agent
labels: [renderer, wiring, agent-renderer]
created: 2026-07-02
---

## Parent

ADR-024: Artifact UI Renderer Integration

## What to build

Update `agent-renderer.ts` to use `renderArtifactUi()` with paper-dossier family for lesson and answer_key artifact types. Currently, `renderAgentArtifact()` calls `renderArtifact("lesson", ...)` and `renderArtifact("answer_key", ...)` which use the old Eta templates with generic styling.

## Current state

`packages/renderer/src/agent-renderer.ts:178-196`:
```typescript
export async function renderAgentArtifact(input: unknown): Promise<string> {
  const artifact = ArtifactContentSchema.parse(input);
  const artifactType = asString(artifact.artifact_type, "lesson");
  switch (artifactType) {
    case "lesson":
      return renderArtifact("lesson", lessonData(artifact));
    case "answer_key":
      return renderArtifact("answer_key", answerKeyData(artifact));
    // ... other types stay on renderArtifact()
  }
}
```

## Target state

```typescript
switch (artifactType) {
  case "lesson":
    return renderArtifactUi({
      family: 'paper-dossier',
      contract: artifact,
      audience: 'teacher',  // or detect from artifact
      kind: 'lesson',
      artifactType: 'lesson',
    });
  case "answer_key":
    return renderArtifactUi({
      family: 'paper-dossier',
      contract: artifact,
      audience: 'teacher',
      kind: 'answer-key',
      artifactType: 'answer_key',
    });
  // ... other types stay on renderArtifact()
}
```

## Acceptance criteria

- [ ] `renderAgentArtifact("lesson", ...)` produces HTML with `data-artifact-theme="paper-dossier"`
- [ ] `renderAgentArtifact("answer_key", ...)` produces HTML with `data-artifact-theme="paper-dossier"`
- [ ] Other artifact types (quiz, worksheet, drill, recap, infographic) continue to use `renderArtifact()` unchanged
- [ ] Lesson output uses `art-*` CSS classes (sidebar, objectives, concept boxes, etc.)
- [ ] Answer-key output uses `art-*` CSS classes (question grid, option states, explanations)
- [ ] All output is standalone HTML (no external assets, brand string present)
- [ ] Existing `agent-renderer.ts` tests still pass
- [ ] The `lessonData()` and `answerKeyData()` adapter functions are either reused or replaced by paper-dossier adapter

## Detailed test suite

- [ ] `packages/renderer/__tests__/agent-renderer.test.ts` (existing): all tests still pass
- [ ] `packages/renderer/__tests__/artifact-ui/agent-renderer-paper-dossier.test.ts`: lesson output contains `data-artifact-theme="paper-dossier"`
- [ ] `packages/renderer/__tests__/artifact-ui/agent-renderer-paper-dossier.test.ts`: answer_key output contains `data-artifact-theme="paper-dossier"`
- [ ] `packages/renderer/__tests__/artifact-ui/agent-renderer-paper-dossier.test.ts`: quiz output still uses `renderArtifact()` (not `renderArtifactUi()`)
- [ ] `packages/renderer/__tests__/artifact-ui/agent-renderer-paper-dossier.test.ts`: lesson output contains sidebar navigation
- [ ] `packages/renderer/__tests__/artifact-ui/agent-renderer-paper-dossier.test.ts`: answer_key output contains question grid

## Verification

- `pnpm --filter @oh-my-class/renderer test` → all tests pass
- `pnpm --filter @oh-my-class/renderer build` → builds successfully
- Manual: render a lesson artifact through agent-renderer, open in browser, verify paper-dossier styling
- Manual: render a quiz artifact, verify it still uses old styling (no regression)

## Blocked by

- `007-public-api-render-artifact-ui.md` — renderArtifactUi() must exist
- `004-contract-adapters-all-families.md` — paper-dossier adapter must exist
- `003-eta-templates-all-families.md` — paper-dossier templates must exist
