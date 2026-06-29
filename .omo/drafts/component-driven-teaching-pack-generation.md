---
slug: component-driven-teaching-pack-generation
status: implemented-focused-slice
intent: clear
pending-action: final broader Pipeline V2 blockers remain outside this slice
approach: Enforce component-first ArtifactContent generation, map those components through existing renderer contracts for every active artifact type, and add organized E2E tests with rich fixture packs that prove generated HTML is assessable.
---

# Draft: component-driven-teaching-pack-generation

## Components (topology ledger)
<!-- Lock the SHAPE before depth. One row per top-level component that can succeed or fail independently. -->
<!-- id | outcome (one line) | status: active|deferred | evidence path -->
- C1 | ContentCreator prompt contract tells the LLM to emit existing component shapes/classes, not raw HTML or one-paragraph sections | active | .omo/evidence/task-1-component-driven-teaching-pack-generation.md
- C2 | Renderer adapter preserves/render-maps components for lesson, worksheet, quiz, drill, recap, and infographic | active | .omo/evidence/task-2-component-driven-teaching-pack-generation.md
- C3 | Rich multi-artifact fixture data covers every active artifact type and gives enough pedagogical/visual detail to judge output quality | active | .omo/evidence/task-3-component-driven-teaching-pack-generation.md
- C4 | E2E tests drive full public/API or graph-render-export flows from fixture to rendered standalone HTML | active | .omo/evidence/task-4-component-driven-teaching-pack-generation.md
- C5 | Evidence/status docs record generated artifact quality and remaining broader Pipeline V2 blockers | active | .omo/evidence/task-5-component-driven-teaching-pack-generation.md

## Implementation status
- Component-first content-creator prompt contract is implemented in `packages/agents/sub_agents/content_creator/prompt_contract.py` and covered by prompt unit tests.
- Rich renderer fixture coverage is implemented in `packages/renderer/__tests__/rich-agent-fixtures.ts` and `packages/renderer/__tests__/agent-renderer-rich-fixtures.test.ts`.
- Checked-in Python E2E coverage is implemented in `tests/e2e/rich_teaching_pack_fixtures.py` and `tests/e2e/test_teaching_pack_component_driven_flow.py`.
- Focused serial verification passed: `37 passed` for Python prompt/E2E tests, `240 passed` for renderer agent-renderer test selection, and renderer `tsc` build passed.
- Broader Pipeline V2 remains incomplete; no `<promise>DONE</promise>` claim is made.

## Open assumptions (announced defaults)
<!-- Record any default you adopt instead of asking, so the user can veto it at the gate. -->
<!-- assumption | adopted default | rationale | reversible? -->
- Artifact scope | Active artifact types are lesson, worksheet, quiz, drill, recap, infographic, plus answer_key where generated teacher-only data exists | Matches AGENTS.md and renderer ArtifactDataMap; reversible by adding export-specific follow-up.
- Component source of truth | Use existing `common/contracts/components/questions.py` and renderer `ContentComponent`/question registry shapes; do not invent a parallel component DSL | Prevents AI from generating bespoke classes/styles; reversible with schema migration.
- E2E approach | Prefer checked-in pytest files with rich deterministic fixtures and renderer assertions over ad-hoc `uv run python - <<PY` drivers | Directly addresses user request #5; reversible only by deleting tests.
- HTML quality bar | A rendered artifact must have multiple meaningful sections/questions/components and pass standalone/no-external/no-student-key checks; a one-section shell is failure | Directly addresses user request #4; reversible by changing test fixture thresholds.

## Findings (cited - path:lines)
- `packages/agents/sub_agents/content_creator/nodes.py:31` builds the single-artifact prompt. Current prompt only says generate one JSON object and does not require existing components, per-artifact richness, or all artifact-type shape guidance.
- `packages/agents/sub_agents/content_creator/nodes.py:121` iterates `artifact_types`, so scalability to every active artifact type can be enforced at the prompt/test layer without changing orchestration shape.
- `packages/renderer/src/agent-renderer.ts:48` preserves `section.components`, but `lessonData` uses it directly while worksheet/quiz/drill/recap/infographic currently flatten mostly to simple text/question arrays.
- `packages/renderer/src/agent-renderer.ts:199` routes `quiz`, `worksheet`, `drill`, `recap`, `infographic`, `answer_key`, and default `lesson` through existing typed renderer pages. This is the seam to prove all active artifacts render with generated styles/classes.
- `packages/renderer/src/contracts/index.ts:22` defines `ArtifactDataMap` with more renderer types than the Teaching Pack active set; this plan must not broaden to unsupported pack flow unless tests prove it.
- `common/contracts/components/questions.py:9` defines `QuestionCard`; `QuestionList` at line 22 defines a reusable section wrapper. These are existing component contracts the LLM prompt should reference by shape.
- `packages/agents/tests/teaching_pack/test_artifact_workflow_node.py:8` covers workflow delegation and scoped regeneration, but fixtures are still minimal and do not prove assessable generated output quality.

## Decisions (with rationale)
- D1: Treat this as implementation work, not a pure audit. The user's bullets explicitly require implementing and adding E2E tests.
- D2: Do not let the LLM generate CSS class names or raw HTML. The renderer owns all styling; the LLM emits typed content sections and known `components` arrays only.
- D3: Add deterministic rich fixture tests first, then adjust prompts/adapter behavior. This protects against regressing into one-section shells while keeping live LLM cost out of CI.
- D4: Cover every active Teaching Pack artifact type in one reusable fixture matrix instead of one-off command probes.
- D5: Preserve package boundaries: packages/agents may reference contracts/common schemas but must not import services/gateway or apps/web.

## Scope IN
- ContentCreator prompt contract for component-first rich ArtifactContent JSON.
- Agent-renderer mapping/preservation needed so all active artifact types use existing renderer pages/components/classes.
- Reusable rich fixture module for lesson, worksheet, quiz, drill, recap, infographic, and answer_key if needed.
- E2E/integration pytest files that render/export rich artifacts and assert quality thresholds.
- Evidence docs for plan progress, verification commands, and generated HTML quality.

## Scope OUT (Must NOT have)
- No GIFT/H5P/QTI/Google Forms implementation in this slice.
- No teacher-gate bypass or self-approval.
- No raw HTML/CSS generated by the LLM as artifact content.
- No new renderer CSS theme source outside `theme.json`/existing template engine.
- No broad full Pipeline V2 completion claim or `<promise>DONE</promise>` until the wider blockers are complete.
- No ad-hoc Python command as the only proof; commands may be used only to run checked-in tests or inspect outputs.

## Open questions
- None blocking. Defaults above are reversible and match the user's explicit constraints.

## Approval gate
status: implementation-authorized-by-ralph-loop
<!-- When exploration is exhausted and unknowns are answered, set status: awaiting-approval. -->
<!-- That durable record is the loop guard: on a later turn read it and resume at the gate instead of re-running exploration. -->
