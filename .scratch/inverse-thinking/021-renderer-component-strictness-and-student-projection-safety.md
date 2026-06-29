---
title: Renderer component strictness and student projection safety
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Tighten renderer component handling. Codegraph found `packages/renderer/src/contracts/components.ts` ends `ContentComponent` with a catch-all `{ type: string; [key: string]: unknown }`, and `agent-renderer.ts` accepts any object with a string `type` as a component. That makes unknown LLM-emitted components silently pass into rendering. Codegraph also found `preserveStudentComponents()` only strips `roleplay_script.answer_key`; other components such as `question_card` still carry `answer`, `explain`, and `wrong_reasons` fields into student data structures.

This slice makes component handling fail closed and separates student/teacher projection policy by component type.

## Acceptance criteria

- [ ] Remove or quarantine the generic catch-all from production `ContentComponent` unions; unknown components produce typed errors.
- [ ] `isContentComponent()` validates against a known component registry, not just object-with-string-type.
- [ ] Student projections strip or transform teacher-only fields for every component type, not only `roleplay_script`.
- [ ] Teacher projections preserve answer/rationale fields in teacher-only output.
- [ ] Renderer errors name the unknown component type and source section ID.
- [ ] Existing valid component fixtures still render unchanged.

## Detailed test suite

- [ ] `packages/renderer/__tests__/components-strictness.test.ts`: Given `{ type: "unknown_component" }`, when rendering through `renderAgentArtifact`, then it fails with `UnknownContentComponentError`.
- [ ] `packages/renderer/__tests__/student-projection-safety.test.ts`: Given a `question_card` with `answer`, `explain`, and `wrong_reasons`, when rendering student output, then answer/rationale fields are absent from visible student HTML.
- [ ] `packages/renderer/__tests__/teacher-projection-safety.test.ts`: Given the same component, when rendering teacher output, then answer/rationale fields are present in teacher-only sections.
- [ ] `packages/renderer/__tests__/roleplay-script-safety.test.ts`: Existing roleplay answer-key stripping behavior remains intact.
- [ ] Type test: `tsc --noEmit` fails if a new component type is added without registry/projection handling.
- [ ] Fuzz test: Given random object components with `type` strings, when passed through component parsing, then only registered component types are accepted.

## Blocked by

- .scratch/inverse-thinking/020-methodology-tag-registry-and-ci-guard.md
- .scratch/inverse-thinking/005-renderer-standalone-html.md
