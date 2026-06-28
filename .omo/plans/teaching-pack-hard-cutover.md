# Teaching Pack Hard Cutover Plan

## TL;DR

Hard-cut runtime/product naming from `pipeline-v2` / `pipeline_v2` / `PipelineV2` to the canonical Teaching Pack domain:

- External routes: `/teaching-packs/runs...`
- Event namespace: `teaching_pack.*`
- Runtime evidence filename: `teaching-pack-run-evidence-{run_id}.md`
- Python classes/modules: `TeachingPack*`, `teaching_pack_*`
- Frontend types/hooks/components: `TeachingPack*`, filenames `teaching-pack-*`, query keys `['teaching-pack', ...]`

No legacy aliases. Old `/pipeline-v2/...` must 404. Historical `.omo` and `.scratch` evidence/plan files are excluded from the purge. Alembic revision IDs/history are stable and must not be rewritten; if current DB object identifiers contain old naming, add a forward migration instead.

## Decisions Locked

1. Scope is full runtime/product hard cutover, not compatibility aliases.
2. Canonical name is Teaching Pack.
3. Routes use plural `/teaching-packs/runs...`.
4. SSE/event namespace is singular `teaching_pack.*`.
5. Rename internal code mechanically, with obvious semantic renames only:
   - `PipelineV2ControlStore` -> `TeachingPackGateStore`
   - `PipelineV2RunStore` -> `TeachingPackRunStore`
   - `PipelineV2SnapshotStore` -> `TeachingPackSnapshotStore`
   - `PipelineV2JobStore` -> `TeachingPackJobStore`
   - `PipelineV2EventVisibility` -> `TeachingPackEventVisibility`
6. Frontend follows `TeachingPack*`, filenames `teaching-pack-*`, query keys `['teaching-pack', ...]`.
7. Runtime evidence filename becomes `teaching-pack-run-evidence-{run_id}.md`.
8. Historical `.omo` / `.scratch` completed evidence remains unchanged unless runtime docs consume it.
9. Warning cleanup target is zero warnings for touched scopes; full-repo unrelated warnings become follow-up issues.

## Must NOT Do

- Do not leave runtime/product aliases for `/pipeline-v2`.
- Do not rewrite historical Alembic revision IDs or old migration history.
- Do not modify generated schemas by hand.
- Do not hide warnings globally; fix source or narrowly assert/suppress expected warnings in the relevant test scope.
- Do not rename completed `.omo` / `.scratch` evidence purely for search cleanliness.
- Do not weaken tests or delete failing tests.

## Todos

- [x] 1. Inventory runtime/product old-name surface
  What to do / Must NOT do: Search `services`, `packages`, `apps`, `tests`, `common`, runtime docs/configs for `pipeline-v2`, `pipeline_v2`, `PipelineV2`, excluding `.omo`, `.scratch`, historical Alembic revision IDs/docstrings unless runtime imports depend on them. Must not rely on one search only; include codegraph/call-site blast radius.
  Acceptance: Checklist names backend modules/classes/events/routes, frontend hooks/components/query keys, test/e2e fixtures, runtime report filenames, warning sources.
  QA: `rg "pipeline-v2|pipeline_v2|PipelineV2" services packages apps tests common docs --glob '!**/node_modules/**'` recorded before and after.

- [x] 2. Backend hard cutover
  What to do / Must NOT do: Rename runtime Python modules/classes/imports/routes/events from PipelineV2/pipeline_v2 to TeachingPack/teaching_pack. Route shape must be `/teaching-packs/runs...`; old `/pipeline-v2/...` must not be registered. Event names must emit `teaching_pack.*`. Runtime evidence reports must use `teaching-pack-run-evidence-{run_id}.md`. Must preserve package boundaries and not rewrite Alembic historical revision IDs.
  Acceptance: Backend tests import new modules/classes; old route returns 404; new route works; search gate has no runtime old-name hits except documented Alembic history if any.
  QA: Targeted `uv run pytest services/gateway/tests ...`, route TestClient/curl checks for old 404/new accepted, SSE event assertion.

- [x] 3. Agent package hard cutover
  What to do / Must NOT do: Rename `packages/agents/pipeline_v2` runtime package to `packages/agents/teaching_pack`, symbols to `TeachingPack*`, stage event strings to `teaching_pack.*`, tests accordingly. Must keep Lead Agent invariant and pure node functions.
  Acceptance: Agent package tests pass; no `packages/agents` runtime old-name hits.
  QA: `uv run pytest packages/agents/tests/pipeline_v2 packages/agents/tests ...` updated paths/names, plus search gate.

- [x] 4. Frontend hard cutover
  What to do / Must NOT do: Rename hooks/types/components/files/query keys to TeachingPack, routes to `/teaching-packs/runs...`, EventSource handling to `teaching_pack.*`. Must not introduce visual/design changes beyond names unless tests require it.
  Acceptance: Frontend tests/build pass for touched scope; old client route strings are gone from `apps`.
  QA: `pnpm --filter web test`, `pnpm --filter web build`, browser or hook-level smoke if app runs.

- [x] 5. Warning cleanup for touched scopes
  What to do / Must NOT do: Eliminate warning output from touched test/build commands. Fix `MODULE_TYPELESS_PACKAGE_JSON`, Next workspace-root warning if touched by web build, provider reasoning-content warning wording, live provider timeout classification, and expected test warnings with local assertions/suppression. Intentional product warnings should become structured results, not noisy logs.
  Acceptance: Touched commands exit 0 with zero warnings or documented unrelated follow-up; no global warning suppression.
  QA: Re-run exact touched Python/TS commands with warning capture.

- [x] 6. Final verification and evidence
  What to do / Must NOT do: Run search gate, route/SSE/API surface QA, targeted tests/builds, LOC checks, package-boundary check, and final warning audit. Write `.omo/evidence/teaching-pack-hard-cutover.md`. Must not claim done with old runtime names still present.
  Acceptance: Evidence records commands/outcomes; `rg` old names across runtime/product scopes returns zero or only approved historical Alembic exceptions; old route 404/new route works; zero warnings for touched scopes.
  QA: Final command bundle plus manual API surface drive.
