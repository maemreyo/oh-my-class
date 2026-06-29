# component-driven-teaching-pack-generation - Work Plan

## TL;DR (For humans)
<!-- Fill this LAST, after the detailed plan below is written, so it summarizes the REAL plan. -->
<!-- Plain English for a non-engineer: NO file paths, NO todo numbers, NO wave/agent/tool names. -->

**What you'll get:** Teaching Pack generation will be forced through existing styled renderer components instead of ad-hoc HTML-like blobs, with rich fixtures that cover lesson, worksheet, quiz, drill, recap, and infographic outputs.

**Why this approach:** The renderer already owns the visual system; the safest fix is to make the AI emit typed content/components and prove every artifact type renders into complete standalone HTML.

**What it will NOT do:** It will not add new export formats, bypass teacher gates, or let the model generate raw HTML/CSS/classes.

**Effort:** Medium
**Risk:** Medium - touches both LLM prompt contracts and renderer/test surfaces.
**Decisions to sanity-check:** Active artifact scope is HTML-first: lesson, worksheet, quiz, drill, recap, infographic; richer exports beyond HTML stay out of scope.

Your next move: Ralph loop continues into implementation under this plan. Full execution detail follows below.

---

> TL;DR (machine): Medium-risk implementation: enforce component-first LLM ArtifactContent, map/render rich components for every active HTML artifact type, and add organized E2E tests/evidence.

## Scope
### Must have
- ContentCreator prompt requires existing component shapes only: sections may include `components` such as `question_card`, `question_list`, `hint_box`, `feedback`, `progress_bar`, `math_block`, `data_chart`, or equivalent already-supported renderer component names; no raw HTML/CSS/classes.
- Every active Teaching Pack artifact type scales through the same path: `lesson`, `worksheet`, `quiz`, `drill`, `recap`, `infographic`.
- Rich artifact fixtures contain enough content to evaluate quality: multiple sections/items/questions, vocabulary/objectives, teacher-only answer material where appropriate, and Vietnamese/English examples where existing tests need them.
- Rendered HTML must be standalone and visually assessable: `<!DOCTYPE html>`, `oh-my-class`, multiple content blocks/cards/questions, no `http(s)://` assets, no student answer-key leakage.
- E2E tests are checked-in pytest files and reusable fixture modules, not one-off shell/Python snippets.
- Plan progress/evidence is updated under `.omo/evidence/` and relevant Pipeline V2 docs if behavior changes.
### Must NOT have (guardrails, anti-slop, scope boundaries)
- Must not add GIFT/H5P/QTI/Google Forms exporters.
- Must not bypass or self-approve teacher gates.
- Must not import `services/*` or `apps/*` from `packages/agents`.
- Must not make LLM-generated raw HTML the source of artifact rendering.
- Must not weaken standalone HTML or answer-key safety invariants.
- Must not claim full Pipeline V2 completion or print `<promise>DONE</promise>` unless all broader blockers are actually complete.

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: TDD for new behavior using pytest for Python graph/E2E and Vitest/renderer tests if renderer adapter changes require TypeScript coverage.
- Evidence: `.omo/evidence/task-<N>-component-driven-teaching-pack-generation.md` plus generated HTML snapshots under `.scratch/pipeline-v2/artifacts/component-driven/` if tests emit examples.

## Execution strategy
### Parallel execution waves
> Target 5-8 todos per wave. Fewer than 3 (except the final) means you under-split.
- Wave 1: Establish fixture/test contract and prompt requirements.
- Wave 2: Implement renderer/adapter/prompt changes against failing tests.
- Wave 3: Run full focused verification, manual surface QA, and evidence updates.

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1 | none | 2,3,4 | none |
| 2 | 1 | 4,5 | 3 |
| 3 | 1 | 4,5 | 2 |
| 4 | 2,3 | 5,6 | none |
| 5 | 4 | 6 | none |
| 6 | 5 | final wave | none |

## Todos
> Implementation + Test = ONE todo. Never separate.
<!-- APPEND TASK BATCHES BELOW THIS LINE WITH edit/apply_patch - never rewrite the headers above. -->
- [x] 1. Add rich component-first fixture contract for all active artifact types
  What to do / Must NOT do: Create reusable checked-in fixture data for `lesson`, `worksheet`, `quiz`, `drill`, `recap`, `infographic`, plus teacher-only answer content where needed. Fixtures must include multiple sections/questions/items and existing component shapes; do not use the weak one-section shell example.
  Parallelization: Wave 1 | Blocked by: none | Blocks: 2,3,4
  References (executor has NO interview context - be exhaustive): `common/contracts/components/questions.py:9`, `common/contracts/components/questions.py:22`, `packages/renderer/src/agent-renderer.ts:48`, `packages/renderer/src/contracts/index.ts:22`, `packages/agents/tests/teaching_pack/test_artifact_workflow_node.py:8`
  Acceptance criteria (agent-executable): New fixture module exposes every active artifact type and each fixture has >=2 student-visible content units; no fixture section title/content contains placeholder strings like `Manual Export`, `[TBD]`, `lorem ipsum`, or `Equivalent fractions practice` as the sole body.
  QA scenarios (name the exact tool + invocation): `uv run pytest <new-fixture-test-file> -q`; happy = all active types pass richness assertions; failure = intentionally minimal fixture helper/fixture is rejected by the same assertion helper. Evidence `.omo/evidence/task-1-component-driven-teaching-pack-generation.md`.
  Commit: N | test(teaching-pack): add rich component fixtures

- [x] 2. Lock ContentCreator prompt to existing components/classes and artifact-specific richness
  What to do / Must NOT do: Update `_build_single_artifact_prompt` and/or prompt helper modules so the LLM is instructed to emit `ArtifactContent` JSON with renderer-supported `components` arrays and artifact-specific shape guidance. Must not instruct the model to generate raw HTML, CSS, or class names.
  Parallelization: Wave 1 | Blocked by: 1 | Blocks: 4
  References (executor has NO interview context - be exhaustive): `packages/agents/sub_agents/content_creator/nodes.py:31`, `packages/agents/sub_agents/content_creator/nodes.py:121`, `packages/renderer/src/contracts/index.ts:22`, `common/contracts/components/questions.py:9`
  Acceptance criteria (agent-executable): Prompt unit test proves prompts for every active artifact type mention component-first JSON, ban raw HTML/CSS/classes, and include type-specific richness requirements.
  QA scenarios (name the exact tool + invocation): `uv run pytest packages/agents/tests/sub_agents/test_content_creator_component_prompt.py -q`; happy = all artifact prompts pass; failure = prompt builder output for unsupported type does not silently broaden scope. Evidence `.omo/evidence/task-2-component-driven-teaching-pack-generation.md`.
  Commit: N | feat(content-creator): require component-first artifacts

- [x] 3. Ensure renderer adapter preserves/maps components for every active artifact type
  What to do / Must NOT do: Extend `packages/renderer/src/agent-renderer.ts` only if tests show components are dropped for non-lesson artifacts. Use existing renderer data contracts/templates; do not create a new styling engine or generated CSS path.
  Parallelization: Wave 1 | Blocked by: 1 | Blocks: 4
  References (executor has NO interview context - be exhaustive): `packages/renderer/src/agent-renderer.ts:48`, `packages/renderer/src/agent-renderer.ts:87`, `packages/renderer/src/agent-renderer.ts:131`, `packages/renderer/src/agent-renderer.ts:146`, `packages/renderer/src/agent-renderer.ts:161`, `packages/renderer/src/agent-renderer.ts:173`, `packages/renderer/src/renderer.ts:32`
  Acceptance criteria (agent-executable): Renderer test renders rich fixtures for all active types and asserts HTML contains existing template/class landmarks plus content from components/questions/items.
  QA scenarios (name the exact tool + invocation): `pnpm --filter @oh-my-class/renderer test -- agent-renderer --runInBand`; happy = all active artifact types render rich HTML; failure = answer_key/teacher-only data is not present in student outputs. Evidence `.omo/evidence/task-3-component-driven-teaching-pack-generation.md`.
  Commit: N | feat(renderer): render component-rich agent artifacts

- [x] 4. Add organized full-flow E2E tests with rich artifact outputs
  What to do / Must NOT do: Add real E2E/integration pytest files that drive the active graph/API-compatible flow from rich generated artifacts to render quality/snapshots/export assertions. Do not rely on one-off inline Python commands as the only test.
  Parallelization: Wave 2 | Blocked by: 2,3 | Blocks: 5,6
  References (executor has NO interview context - be exhaustive): `packages/agents/teaching_pack/nodes.py`, `packages/agents/teaching_pack/graph.py`, `services/gateway/teaching_pack_export_writer.py`, `packages/agents/tests/teaching_pack/test_artifact_workflow_node.py:8`, `.scratch/pipeline-v2/artifacts/live-v2-preview-export-evidence-2026-06-28.md`
  Acceptance criteria (agent-executable): New E2E file includes at least two full flows: all-active-artifact rich generation/render quality, and scoped rejection preserving accepted artifacts while regenerating a rich rejected artifact. Tests assert standalone HTML invariants and minimum richness thresholds.
  QA scenarios (name the exact tool + invocation): `uv run pytest tests/e2e/test_teaching_pack_component_driven_flow.py -q` or an equivalent repo-consistent E2E path; happy = full rich pack passes; failure = minimal shell artifact fails richness assertion. Evidence `.omo/evidence/task-4-component-driven-teaching-pack-generation.md`.
  Commit: N | test(e2e): cover component-driven teaching pack flows

- [x] 5. Update evidence/progress docs after implementation
  What to do / Must NOT do: Update this plan, `.omo/drafts`, and relevant Pipeline V2 evidence docs with exact commands, pass counts, and generated HTML sample paths. Must not claim full Pipeline V2 completion.
  Parallelization: Wave 3 | Blocked by: 4 | Blocks: 6
  References (executor has NO interview context - be exhaustive): `.omo/plans/component-driven-teaching-pack-generation.md`, `.scratch/pipeline-v2/artifacts/live-v2-preview-export-evidence-2026-06-28.md`, `.omo/plans/pipeline-v2-completion.md`
  Acceptance criteria (agent-executable): Evidence files list the checked-in E2E test file(s), command outputs, artifact types covered, and remaining blockers.
  QA scenarios (name the exact tool + invocation): `rg "component-driven|rich artifact|all active artifact" .omo .scratch/pipeline-v2 -n`; happy = evidence references current tests and no `<promise>DONE</promise>` is present. Evidence `.omo/evidence/task-5-component-driven-teaching-pack-generation.md`.
  Commit: N | docs(pipeline-v2): record component-driven evidence

- [x] 6. Run final verification and manual surface QA
  What to do / Must NOT do: Run targeted Python/TypeScript tests, py_compile/ts build where touched, LOC checks, diff hygiene, and a manual artifact rendering/export surface check using checked-in fixtures. Must not skip browser/HTML inspection if UI/rendered output changed.
  Parallelization: Wave 3 | Blocked by: 5 | Blocks: final verification wave
  References (executor has NO interview context - be exhaustive): AGENTS.md hard invariants 01-10; this plan's Verification strategy.
  Acceptance criteria (agent-executable): Targeted test commands pass; generated sample HTML contains multiple visible content units, `<!DOCTYPE html>`, `oh-my-class`, no `http://`/`https://`, no answer-key markers in student outputs; all changed source/test files under 250 pure LOC or split.
  QA scenarios (name the exact tool + invocation): `uv run pytest ...`, `pnpm --filter @oh-my-class/renderer test ...`, `uv run python -m py_compile ...`, `GIT_MASTER=1 git diff --check`, and browser/HTML surface via renderer output or Playwright if web UI changed. Evidence `.omo/evidence/task-6-component-driven-teaching-pack-generation.md`.
  Commit: N | verify(component-driven): final focused checks

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [x] F1. Plan compliance audit
- [x] F2. Code quality review
- [x] F3. Real manual QA
- [x] F4. Scope fidelity

## Commit strategy
- Do not commit unless explicitly requested.
- Keep changes grouped by behavior: prompt/agent, renderer mapping, E2E fixtures/tests, evidence docs.
- Never stage unrelated existing dirty worktree files.

## Success criteria
- All active artifact types can be generated as component-first JSON and rendered through existing renderer pages/classes.
- E2E tests prove rich, assessable HTML output instead of one-section shells.
- Tests are checked into organized files and reusable fixtures; no ad-hoc command is the only proof.
- Standalone HTML and answer-key invariants stay enforced.
- Evidence/progress docs are updated with commands and remaining broader blockers.
- Final verification wave F1-F4 approves before any completion promise.
