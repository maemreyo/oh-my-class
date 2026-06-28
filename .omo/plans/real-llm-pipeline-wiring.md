# real-llm-pipeline-wiring - Work Plan

## TL;DR (For humans)
**What you'll get:** The teaching-pack pipeline will generate lesson, worksheet, and quiz content one artifact at a time through the real model, then prove the full teacher approval and HTML export flow through the live gateway.

**Why this approach:** The current all-at-once generation call is too large for 4omc and gets truncated. Splitting generation by artifact fixes the runtime failure while preserving the existing graph, teacher gates, and package boundaries.

**What it will NOT do:** It will not bypass human approval gates, it will not add new export formats, and it will not hide real model failures behind placeholder content.

**Effort:** Medium
**Risk:** Medium - real LLM calls are slow and may fail upstream, so the plan requires local tests first and serial live scenario evidence.
**Decisions to sanity-check:** HTML-only export first; per-artifact generation inside the agent package; service orchestrator used as design evidence only, not imported.

Your next move: approve execution with `$start-work .omo/plans/real-llm-pipeline-wiring.md`, or ask for a high-accuracy review first. Full execution detail follows below.

---

> TL;DR (machine): Medium-risk pipeline stabilization: per-artifact content generation, component-aware gates/export checks, and live 9router gateway E2E evidence before broad scenarios.

## Scope
### Must have
- Replace active content generation behavior so each requested artifact type is generated in a separate LLM call and validated independently before returning the existing graph shape `{"artifacts": [...]}`.
- Preserve active graph topology and package boundaries: `packages/agents` must not import `services/gateway`.
- Retain successful artifacts when a later artifact fails, while still failing the graph step unless all requested required artifacts pass.
- Make schema/content/judge/export checks component-aware so real LLM output that uses `section.components` is reviewed and scored.
- Prevent fallback placeholder artifacts from satisfying success criteria in real-flow testing.
- Keep teacher approval gates intact and verify them through gateway approve endpoints.
- Stabilize HTML export only; render standalone HTML with no external `http(s)://` references.
- Run real 9router `:20228` / model `4omc` E2E scenarios after local checks pass, recording logs/evidence.

### Must NOT have (guardrails, anti-slop, scope boundaries)
- Must NOT import from `services/*` or `apps/*` inside `packages/agents`, `packages/quality`, `packages/renderer`, or `common`.
- Must NOT bypass, auto-approve, mock, or short-circuit teacher gates in production code.
- Must NOT broaden export implementation to GIFT/H5P/QTI in this slice.
- Must NOT weaken artifact schema/content gates merely to accept malformed LLM output.
- Must NOT report success based only on unit tests or source inspection; live gateway use is required.
- Must NOT revert or overwrite unrelated dirty worktree changes.

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: tests-after + pytest for Python package behavior, existing renderer build command for HTML finalize, and live gateway HTTP E2E via `scripts/test_e2e_real_llm.py`.
- Evidence: `.omo/evidence/task-<N>-real-llm-pipeline-wiring.<ext>` for task-local commands, plus `.omo/evidence/final-real-llm-pipeline-wiring.md` for the final live scenario matrix.
- Local checks before live LLM calls:
  - `uv run pytest packages/agents/gates/tests/test_quality_gates.py packages/agents/tests/sub_agents/test_content_creator_prompt_size.py services/gateway/tests/test_quality_gate_integration.py`
  - `uv run pytest services/gateway/tests/test_artifact_workflow.py` to ensure service orchestration remains untouched.
  - `pnpm --dir packages/renderer build` if finalize or renderer-facing shape changes.
  - `lsp_diagnostics` on every changed Python/TypeScript source file.
- Live manual QA gate:
  - Start/restart gateway on `:8001` with `.env` pointing to `LLM_BASE_URL=http://localhost:20228/v1`, `NINEROUTER_BASE_URL=http://localhost:20228/v1`, model `4omc`.
  - Run `uv run python scripts/test_e2e_real_llm.py --scenario math_simple --timeout 1800`.
  - Approve blueprint and content through the gateway approval surface if the script does not already do so.
  - Inspect exported HTML payloads for `<!DOCTYPE html>`, `oh-my-class`, and absence of `http://`/`https://` asset references.

## Execution strategy
### Parallel execution waves
> Target 5-8 todos per wave. Fewer than 3 (except the final) means you under-split.
- Wave 1: shared extraction and content-creator unit seams. These are independent if kept in separate helpers/tests.
- Wave 2: wire per-artifact generation and harden gates/finalize around the helpers.
- Wave 3: update real E2E harness and run local package checks.
- Wave 4: live 9router scenario runs and final evidence synthesis.

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1 | none | 3,4,5 | 2 |
| 2 | none | 3,6 | 1 |
| 3 | 1,2 | 7,8 | 4,5 |
| 4 | 1 | 7,8 | 3,5,6 |
| 5 | 1 | 7,8 | 3,4,6 |
| 6 | 2 | 7,8 | 4,5 |
| 7 | 3,4,5,6 | 8, final | none |
| 8 | 7 | final | none |

## Todos
> Implementation + Test = ONE todo. Never separate.
<!-- APPEND TASK BATCHES BELOW THIS LINE WITH edit/apply_patch - never rewrite the headers above. -->
- [x] 1. Add shared artifact text/external URL extraction helpers for component-first content.
  What to do / Must NOT do: Create package-local helpers under `packages/agents/gates/` or another existing package-appropriate module that recursively extract student-facing text and URLs from `sections[*].content`, `sections[*].components`, nested question/card/list/callout fields, and teacher-only boundaries. Must NOT treat `teacher_only` answer-key sections as student-facing text for leakage checks unless the target checker explicitly needs teacher-only data.
  Parallelization: Wave 1 | Blocked by: none | Blocks: 3,4,5
  References (executor has NO interview context - be exhaustive): `packages/agents/gates/schema_validator.py:32`, `packages/agents/gates/content_reviewer.py:35`, `packages/agents/gates/llm_judge.py:13`, `packages/agents/nodes/finalize.py:35`, `common/contracts/artifact.py:46`
  Acceptance criteria (agent-executable): Add pytest coverage proving extraction includes text inside paragraph/heading/callout/question_list components, excludes teacher-only text for student-facing mode, and returns nested external URLs. Run `uv run pytest packages/agents/gates/tests/test_quality_gates.py -k "component or external or content"` and save output to `.omo/evidence/task-1-real-llm-pipeline-wiring.txt`.
  QA scenarios (name the exact tool + invocation): happy: pytest fixture with component-only lesson returns non-empty extracted text; failure: fixture with `https://cdn.example.com/x.png` nested inside a component returns that URL and fails finalize/gate checker. Evidence `.omo/evidence/task-1-real-llm-pipeline-wiring.txt`.
  Commit: Y | refactor(gates): add component-aware artifact extraction

- [x] 2. Split content creator prompting into one-artifact payloads without changing the graph return shape.
  What to do / Must NOT do: Refactor `packages/agents/sub_agents/content_creator/nodes.py` so the prompt builder can target exactly one `artifact_type`, require a single `ArtifactContent` object from the LLM, and validate that the returned object's `artifact_type` matches the requested type. Keep `content_creator_graph_node` returning `{"artifacts": [...]}`. Must NOT import or call `services/gateway/artifact_workflow.py`.
  Parallelization: Wave 1 | Blocked by: none | Blocks: 3,6
  References (executor has NO interview context - be exhaustive): `packages/agents/sub_agents/content_creator/nodes.py:28`, `packages/agents/sub_agents/content_creator/nodes.py:40`, `packages/agents/sub_agents/content_creator/nodes.py:91`, `packages/agents/sub_agents/content_creator/agent.py:36`, `packages/agents/sub_agents/content_creator/adapters.py:8`, `services/gateway/artifact_workflow.py:103`
  Acceptance criteria (agent-executable): Unit test monkeypatches `compiled_json_chat` and asserts three requested artifact types trigger three calls, each prompt contains only the target artifact type, and output order matches request order. Run `uv run pytest packages/agents/tests/sub_agents/test_content_creator_prompt_size.py packages/agents/tests/sub_agents -k content_creator` and save output to `.omo/evidence/task-2-real-llm-pipeline-wiring.txt`.
  QA scenarios (name the exact tool + invocation): happy: fake LLM returns valid single objects for lesson/worksheet/quiz and node returns three artifacts; failure: fake LLM returns `artifact_type="lesson"` for a quiz request and node retries/fails with target mismatch. Evidence `.omo/evidence/task-2-real-llm-pipeline-wiring.txt`.
  Commit: Y | refactor(content-creator): generate artifacts one at a time

- [x] 3. Add per-artifact retry/failure metadata and reject placeholder success.
  What to do / Must NOT do: Ensure each artifact generation has bounded retries and records artifact type, attempt, error class, and last validation message in failure context. If any requested artifact fails after retries, return a graph failure signal or raise so healing handles it; do not return placeholder artifacts as success. Existing placeholder builder may remain only for explicit escalation/user-visible failure content, not for `schema_valid` success.
  Parallelization: Wave 2 | Blocked by: 1,2 | Blocks: 7,8
  References (executor has NO interview context - be exhaustive): `packages/agents/sub_agents/content_creator/nodes.py:83`, `packages/agents/sub_agents/content_creator/nodes.py:119`, `packages/agents/sub_agents/content_creator/nodes.py:130`, `packages/agents/sub_agents/content_creator/nodes.py:170`, `packages/agents/healing/orchestrator.py:55`
  Acceptance criteria (agent-executable): Tests prove one failed artifact does not discard already generated artifacts in internal metadata, but the node does not report overall success unless all requested artifacts validate; placeholder metadata cannot pass the success path. Run `uv run pytest packages/agents/tests/sub_agents -k content_creator` and save output to `.omo/evidence/task-3-real-llm-pipeline-wiring.txt`.
  QA scenarios (name the exact tool + invocation): happy: first artifact succeeds, second retries once then succeeds; returned artifacts include both in order. failure: second artifact fails all attempts; result raises/returns failure and no placeholder artifact is treated as generated success. Evidence `.omo/evidence/task-3-real-llm-pipeline-wiring.txt`.
  Commit: Y | fix(content-creator): fail closed on per-artifact generation errors

- [x] 4. Wire component-aware extraction through schema/content review and judge scoring.
  What to do / Must NOT do: Update `step_10_content_review` and `step_10b_llm_judge` to use the helper from Todo 1 so component-only real LLM artifacts are fact/age reviewed and scored. Keep schema validation's existing acceptance of component-only sections, but add tests for generated component patterns. Must NOT lower `judge_min_score` or disable methodology/component checks.
  Parallelization: Wave 2 | Blocked by: 1 | Blocks: 7,8
  References (executor has NO interview context - be exhaustive): `packages/agents/gates/schema_validator.py:40`, `packages/agents/gates/content_reviewer.py:20`, `packages/agents/gates/content_reviewer.py:49`, `packages/agents/gates/llm_judge.py:39`, `packages/quality/layer2_content/component_scorer.py` via `packages/agents/gates/llm_judge.py:7`
  Acceptance criteria (agent-executable): Component-only lesson with enough real text passes schema/content review and gets a non-zero judge score; empty component-only artifact fails. Run `uv run pytest packages/agents/gates/tests/test_quality_gates.py` and save output to `.omo/evidence/task-4-real-llm-pipeline-wiring.txt`.
  QA scenarios (name the exact tool + invocation): happy: paragraph/heading components are included in judge word count; failure: artifact with only empty components fails content/schema review. Evidence `.omo/evidence/task-4-real-llm-pipeline-wiring.txt`.
  Commit: Y | fix(quality-gates): review component-first artifacts

- [x] 5. Harden export readiness and finalize for standalone HTML from nested content.
  What to do / Must NOT do: Update `step_11_export_readiness` only for HTML requirements in this slice, and update `step_12_finalize` external URL checks to inspect nested component payloads via Todo 1 helper. Avoid rebuilding renderer once per artifact if a minimal safe improvement is straightforward, but do not refactor renderer architecture. Must NOT add GIFT/H5P/QTI export support.
  Parallelization: Wave 2 | Blocked by: 1 | Blocks: 7,8
  References (executor has NO interview context - be exhaustive): `packages/agents/gates/export_readiness.py:11`, `packages/agents/gates/export_readiness.py:17`, `packages/quality/layer6_export/export_validator.py:68`, `packages/agents/nodes/finalize.py:18`, `packages/agents/nodes/finalize.py:35`, `packages/agents/nodes/finalize.py:53`
  Acceptance criteria (agent-executable): Nested external URLs block finalize/export; clean component-first artifacts render to HTML containing `<!DOCTYPE html>` and `oh-my-class`. Run `uv run pytest packages/agents/gates/tests/test_quality_gates.py services/gateway/tests/test_quality_gate_integration.py` and `pnpm --dir packages/renderer build`; save output to `.omo/evidence/task-5-real-llm-pipeline-wiring.txt`.
  QA scenarios (name the exact tool + invocation): happy: sample lesson artifact renders standalone HTML; failure: nested component URL `https://cdn.example.com/a.css` produces export/finalize failure. Evidence `.omo/evidence/task-5-real-llm-pipeline-wiring.txt`.
  Commit: Y | fix(export): validate nested content before html finalize

- [x] 6. Update real-LLM E2E harness to prove actual gate resumes and per-artifact progress.
  What to do / Must NOT do: Ensure `scripts/test_e2e_real_llm.py` starts a run through the gateway, observes blueprint gate, approves via `POST /{run_id}/approve`, observes content gate, approves via the same endpoint, then confirms final export status/artifacts. Log per-step timings, LLM base URL/model, artifact types produced, and failure context. Must NOT use mock LLM env vars or direct node calls.
  Parallelization: Wave 2 | Blocked by: 2 | Blocks: 7,8
  References (executor has NO interview context - be exhaustive): `scripts/test_e2e_real_llm.py`, `services/gateway/routers/approvals.py:81`, `services/gateway/routers/approvals.py:103`, `services/gateway/routers/runs.py` from codegraph not shown in source, `packages/agents/graph.py:261`
  Acceptance criteria (agent-executable): A dry-run/local fake mode if present proves the script calls approval endpoints; real mode refuses to run when `LLM_BASE_URL` is not `:20228` unless explicitly overridden. Run `uv run python scripts/test_e2e_real_llm.py --help` plus any script unit/smoke tests and save output to `.omo/evidence/task-6-real-llm-pipeline-wiring.txt`.
  QA scenarios (name the exact tool + invocation): happy: script logs both `blueprint_approval` and `content_approval` resume events; failure: with wrong base URL env, script exits before spending LLM calls. Evidence `.omo/evidence/task-6-real-llm-pipeline-wiring.txt`.
  Commit: Y | test(e2e): drive real approval gates in llm scenario

- [x] 7. Run local verification and fix only failures caused by this plan.
  What to do / Must NOT do: Run diagnostics/tests after all code changes; fix failures caused by the implementation. Record pre-existing unrelated failures separately and do not broaden scope. Must NOT delete/weaken tests.
  Parallelization: Wave 3 | Blocked by: 3,4,5,6 | Blocks: 8, final
  References (executor has NO interview context - be exhaustive): `packages/agents/gates/tests/test_quality_gates.py:326`, `services/gateway/tests/test_quality_gate_integration.py`, `services/gateway/tests/test_artifact_workflow.py`, `packages/agents/tests/sub_agents/test_content_creator_prompt_size.py`
  Acceptance criteria (agent-executable): `lsp_diagnostics` clean for changed files; `uv run pytest packages/agents/gates/tests/test_quality_gates.py packages/agents/tests/sub_agents/test_content_creator_prompt_size.py services/gateway/tests/test_quality_gate_integration.py services/gateway/tests/test_artifact_workflow.py` exits 0 or records unrelated pre-existing failures with evidence; renderer build exits 0 if touched. Save outputs to `.omo/evidence/task-7-real-llm-pipeline-wiring.txt`.
  QA scenarios (name the exact tool + invocation): happy: all targeted tests pass; failure: inject/retain a fixture with nested invalid URL and prove the relevant test fails before the fix or passes by detecting it after the fix. Evidence `.omo/evidence/task-7-real-llm-pipeline-wiring.txt`.
  Commit: Y | test(pipeline): verify per-artifact generation locally

- [x] 8. Run live 9router full-flow scenarios serially and capture final evidence.
  What to do / Must NOT do: Restart gateway on `:8001` using `.env` with `LLM_BASE_URL=http://localhost:20228/v1`, `NINEROUTER_BASE_URL=http://localhost:20228/v1`, model `4omc`, and no mock LLM flags. Run `math_simple` first with a long timeout; if it passes, run at least one non-math scenario. Capture gateway logs, script output, run IDs, gate approvals, artifact counts/types, export status, and rendered HTML invariant checks. Must NOT continue broad scenario runs after a new systemic failure; diagnose and return to the relevant todo.
  Parallelization: Wave 4 | Blocked by: 7 | Blocks: final
  References (executor has NO interview context - be exhaustive): `.env`, `scripts/test_e2e_real_llm.py`, `packages/agents/graph.py:179`, `services/gateway/routers/approvals.py:81`, `/tmp/gateway.log`
  Acceptance criteria (agent-executable): `uv run python scripts/test_e2e_real_llm.py --scenario math_simple --timeout 1800` reaches completed/exported state with lesson+worksheet+quiz artifacts; one additional scenario reaches at least content approval or completed state, with any upstream 9router timeout classified. Save matrix to `.omo/evidence/final-real-llm-pipeline-wiring.md`.
  QA scenarios (name the exact tool + invocation): happy: live run completes through export and generated HTML has doctype/brand/no external asset URL. failure: intentionally wrong `LLM_BASE_URL` or stopped gateway causes script to fail fast without marking scenario pass. Evidence `.omo/evidence/task-8-real-llm-pipeline-wiring.txt` and `.omo/evidence/final-real-llm-pipeline-wiring.md`.
  Commit: N | live evidence only unless harness fixes are required

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [x] F1. Plan compliance audit: read this plan and changed files; verify every Must have is satisfied and every Must NOT have is preserved. Evidence `.omo/evidence/f1-real-llm-pipeline-wiring.md`.
- [x] F2. Code quality review: review package boundaries, retry logic, prompt sizing, placeholder fail-closed behavior, and no `as any`/type ignores added. Evidence `.omo/evidence/f2-real-llm-pipeline-wiring.md`.
- [x] F3. Real manual QA: independently drive the live gateway run and approval surface, not just inspect script logs. Evidence `.omo/evidence/f3-real-llm-pipeline-wiring.md`.
- [x] F4. Scope fidelity: verify no GIFT/H5P/QTI implementation, no teacher-gate bypass, no mock env in live run, and no unrelated dirty worktree changes overwritten. Evidence `.omo/evidence/f4-real-llm-pipeline-wiring.md`.

## Commit strategy
- Prefer 4 atomic commits if the user asks to commit:
  1. `refactor(content-creator): generate artifacts one at a time`
  2. `fix(quality-gates): review component-first artifacts`
  3. `fix(export): validate nested content before html finalize`
  4. `test(e2e): drive real approval gates in llm scenario`
- Do not commit `.env` secrets or transient logs. Evidence under `.omo/evidence/` may be committed only if this repo treats `.omo` plans/evidence as tracked work artifacts; otherwise leave them uncommitted and report paths.
- Before any commit: inspect `git status`, `git diff`, and `git log --oneline -10`; stage only intended files.

## Success criteria
- Active full-flow graph no longer asks one LLM call to generate all artifacts.
- Per-artifact generation returns valid `ArtifactContent` objects in requested order and fails closed on unrecoverable artifact errors.
- Component-first artifacts are schema-validated, content-reviewed, judged, and export-checked using nested text/URL extraction.
- HTML finalization blocks nested external URLs and produces standalone HTML for clean artifacts.
- Teacher gates are verified through gateway approval endpoints in live or live-equivalent E2E, not bypassed.
- Targeted pytest/renderer checks pass, or unrelated pre-existing failures are documented with evidence.
- At least `math_simple` passes through real 9router `:20228` / `4omc` full flow to export, with one additional scenario attempted and classified.
