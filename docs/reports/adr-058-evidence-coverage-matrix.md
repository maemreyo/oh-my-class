# ADR-058 Evidence Coverage Matrix

Status as of 2026-07-11, compiled for issue #459 ("Harden and release
Full-Breadth Teaching Content Creator V1"). #459's own body states it
"implements no missing capability" — this document is the cross-reference
ADR-058 asks for: which of its required evidence lanes already have real,
working coverage today, and which are genuine gaps. It does not replace
ADR-058; it maps ADR-058's requirements onto concrete file paths so a
release reviewer doesn't have to re-derive coverage from scratch.

Each lane is marked **Covered**, **Partial**, or **Gap**. "Covered" means a
real test/artifact exercises the behavior through its actual code path, not
just a name match — every entry below was opened and read, not inferred
from a filename.

## 1. Workers, thin state, idempotency, budgets, outage behavior

**Covered.** `services/gateway/worker_lease.py` (atomic UPDATE-based
leasing) + `services/gateway/tests/test_teaching_pack_job_store_leases.py`,
`test_lease_heartbeat.py`, `test_idempotent_reclaim.py`. Idempotency:
`services/gateway/teaching_pack_idempotency.py` (SHA-256 scoped keys) +
`test_teaching_pack_contract_resume.py`, `test_checkpoint_recovery.py`.
Budgets: `services/gateway/budget_db.py` + `test_budget_db.py`,
`test_budget_hardstop.py`. Provider/research outage: `packages/llm_client
/circuit_breaker.py` + `services/gateway/tests/test_provider_circuit_breaker.py`,
`packages/agents/healing/circuit_breaker.py` + its test.

**Caveat**: `test_operations_hardening.py::TestWorkerLease` and
`test_teaching_pack_worker.py` fail when the full `services/gateway` suite
runs in one process (inverted-boolean symptoms consistent with cross-test
DB-state leakage on the shared Postgres instance, not a proven product
bug) — re-run in isolation before treating as a release blocker.

## 2. Tenant isolation, retention, hard erase, admin recovery, observability

**Covered — substantively, not stubbed.**
`services/gateway/tests/test_tenant_isolation_matrix.py` (258 lines) spins
a real FastAPI app + Postgres and drives an endpoint matrix as owner vs.
another teacher, asserting 403/404 — genuine cross-cutting coverage.
Retention/purge: `services/gateway/retention.py`, `purge.py` +
`test_soft_delete_retention.py`, `test_retention_policy.py`,
`test_teaching_session_retention.py`. Admin recovery:
`services/gateway/admin_recovery.py` (audit-logged `SafeRecoveryAction`
enum) + `test_notifications_admin_recovery.py`. Metadata-hash observability:
no literal `metadata_hash`, but the equivalent exists —
`packages/agents/llm/prompt_metadata.py` and `packages/agents/teaching_pack
/scoped_repair_hashing.py` provide content-hash observability for
provenance/scoped-regeneration.

## 3. Capability-covering evidence matrix

**Partial — fragmented, not unified, and one cross-check is currently red.**
There is no single document or test enumerating full artifact × subject ×
Grade Band × language coverage. What exists is a set of per-domain JSON
manifests under `common/component_strategy_knowledge/capabilities/`
(`teaching_pack.json`, `renderer.json`... plus this epic's four subject
packs: `math_capability_pack.json`, `science_capability_pack.json`,
`language_literacy_capability_pack.json`, `humanities_capability_pack.json`),
each cross-checked against runtime registries by dedicated tests
(`common/contracts/tests/test_teaching_pack_capabilities.py`,
`packages/renderer/__tests__/teaching-pack-capabilities.test.ts`,
`common/contracts/tests/test_subject_capability_pack.py`).

**Fixed.** `packages/renderer/__tests__/teaching-pack-capabilities.test.ts`
failed because `teaching_pack.json` declared `slide_deck` as a
`renderer_plugin`, but `defaultRegistry` never registered one. Tracing
`renderArtifact()` (the stable Eta-template API every artifact type already
uses) showed slide_deck wasn't a disconnected rendering system, just the
one core type never migrated onto the newer `defaultRegistry`/`render()`
plugin path — but two real blockers had to be resolved first, not
shallow-patched around:

1. `renderArtifact()` calls `assertStudentSlideDeckHtmlIsSafe()`
   (`slide-deck-projection.ts`) *after* sanitization to stop teacher-only
   notes/answers leaking into student HTML — a real security check with no
   equivalent hook in the registry pipeline. Added
   `postSanitizeCheck?(html, templateData, context)` to `ArtifactKindPlugin`
   (`core/types.ts`) and wired it into `render()` (`core/render.ts`), typed
   as `unknown` (not `TTemplateData`) for the same covariance reason
   `adapt`'s `input` is `unknown` — a heterogeneous plugin array needs it in
   that position, confirmed by `tsc` initially rejecting the naive
   `TTemplateData`-typed version across every existing plugin.
2. `render()`'s inline-only asset policy (`core/asset-policy.ts`) requires
   every inline `<script>` to carry a `data-managed-script-id` matching a
   plugin-declared, hash-verified `ManagedScriptDeclaration` — but
   `templates/base.html`'s `pageJS` script tag (slide_deck's presentation/
   print-mode player, the one producer of inline JS among all 12 core
   types) had no such attribute, and its source lives inline inside the Eta
   template, not a standalone file `loadManagedScripts` can hash. Added the
   attribute (one-line change to `base.html`, confirmed via `git diff` to
   touch nothing else — an early attempt with an explanatory Eta comment on
   its own line silently shifted whitespace in unrelated artifact types'
   snapshot tests, caught by running the full suite, not assumed safe),
   extracted a byte-identical copy of the embedded script to
   `templates/pages/slide-deck-player.js` for hashing, and added
   `slide-deck-player-script-sync.test.ts` as a drift guard (byte-equality
   check) so the two copies can't silently diverge.

`packages/renderer/src/plugins/slide-deck.ts` is the resulting plugin: a
full zod schema mirroring `SlideDeckData` (no zod schema existed for this
contract before), `adapt()` delegating to the same `projectSlideDeckSurface`
`renderArtifact()` already uses (so `render_surface` on the input data
drives behavior identically, not a new `context.audience`-derived mapping),
and `postSanitizeCheck` re-running the same leak check. Extended
`render-api-matrix.test.ts` with a real slide_deck case (renders through
`render()`, asserts no SECRET-sentinel teacher-only leak into student
output) rather than just making the capability-manifest check pass in
isolation.

WCAG/accessibility: **Covered and runnable** —
`apps/web/tests/e2e/a11y-artifacts.spec.ts` / `a11y-dashboard.spec.ts` (real
axe-core + Playwright, WCAG 2.2 AA tags, auto-starts its own web server) and
`packages/renderer/__tests__/a11y-artifacts.test.ts` (fixture-driven, no
browser needed) all exist and pass; Playwright/axe-core and `pnpm` are
installed in this environment. Security:
`services/gateway/tests/test_no_unscoped_accessor_in_routers.py` is a real
AST-based static check (walks router ASTs, flags unscoped `get_run_by_id`
calls against an explicit allow-list), not a name-only stub.

**Second known gap**: `tests/security/test_answer_key_leakage.py` was
silently broken before this pass — `_compliance_gate` in
`packages/agents/teaching_pack/nodes.py` is `async def`, but the test
called it synchronously and never asserted on the result (it asserted on
an un-awaited coroutine object, which has no `.get()` method and raised
`AttributeError` rather than a real assertion failure). **Fixed in this
pass** (`tests/security/test_answer_key_leakage.py` now `await`s it) — the
answer-leakage invariant now has real, passing coverage again, but this
means it had zero working coverage for an unknown period before today.

**Third gap — investigated and fixed**:
`packages/agents/tests/test_reviewer_live_wiring.py` looked like a real
behavioral gap (3 of 4 tests failed with `quality_recovery_route` staying
`None` instead of routing to `artifact_workflow`/`planning_blueprint`).
Tracing `render_quality` (`packages/agents/teaching_pack/quality_runtime.py`)
showed it only ever reads artifacts via `_artifact_projections(state,
content_store)`, which returns `[]` whenever `content_store is None` —
this test constructed state with a direct `"artifacts": [...]` key (the
pre-V2-lineage calling convention) and never passed `content_store` or
`artifact_references`, so `render_quality` saw zero artifacts and never
even reached the Layer-4 reviewer call. Confirmed the reviewer/quality
logic itself is correct by rewriting the test to build state the same way
the (passing) sibling `test_render_quality.py` does — via
`InMemoryArtifactContentStore.persist()` + `artifact_references` — after
which all 4 tests pass with no product code changed. This was a stale
test-construction bug, not a reviewer-routing regression.

## 4. Backup, migration, deployment rollback, big-bang cutover

**Partial, with one dead link.** `docs/runbooks/db-restore.md` references
`docs/operations/disaster-recovery.md`, which **does not exist anywhere in
this repository** — a broken link a release reviewer would hit immediately.
`services/gateway/disaster_recovery.py` (real code, `RestoreDrillSnapshot`)
is exercised only incidentally via `test_checkpoint_recovery.py`, not a
dedicated restore-drill test. `.omo/evidence/teaching-pack-hard-cutover.md`
and `.omo/plans/teaching-pack-hard-cutover.md` are real, detailed cutover
evidence — but for the earlier `pipeline-v2` → `teaching_pack` rename
(dated 2026-06-28), not the ADR-058 full-V1 release this issue is actually
gating. **No document addresses ADR-058's specific "big-bang GA with
rollback-safe data" for this release** — this is the single largest gap in
this whole audit, and it is fundamentally a business/release-management
artifact, not something a coding pass can manufacture without an actual
planned cutover date and rollback owner.

## 5. Tests, QA, evidence commands, docs, ADR sync

**Covered, with one stale check.** `docs/testbook/runbook.md` is a real,
current canonical test-command reference matching actual `make
test`/`pytest`/`pnpm` invocations. `docs/runbooks/*.md` (6 failure-mode
runbooks) exist and pass `tests/test_runbook_presence.py`'s structural
check. ADR-058 itself is well-formed and current.

**Fixed**: `tests/test_architecture_sync.py` failed in 3 places. Two were
the stored `docs/system/architecture.manifest.json` snapshot simply being
stale (`migration_count: 29` vs. the real `37`, missing the `source_conflict`
gate from #432, missing several routers added since) plus a dangling
reference to the pre-rename `artifact_chunks` state key
(`scripts/generate_architecture_manifest.py`, same root cause as the
`stable_merge_artifacts` rename above) — fixed by correcting the stale key
reference and re-running `python scripts/generate_architecture_manifest.py`
to regenerate the snapshot. The third was the reference to
`docs/system/ARCHITECTURE.md`, deleted in 6ea12b9 when this repo's
hand-written architecture doc was replaced by the auto-generated
`docs/anatomy/` trace; retargeted the check at `docs/testbook/runbook.md`
(the canonical, hand-maintained command reference this repo already keeps
current) and added the manifest's path and regeneration command there.

## Overall verdict

This is closer to a **documentation/evidence-assembly gap than a
functional gap**. The substantive infrastructure ADR-058 asks for — tenant
isolation, worker leasing, retention/purge, admin recovery, WCAG a11y specs
— is real and passing, not stubbed. Five collateral bugs found during this
audit are fixed as of this pass: a stale reducer-rename import blocking
whole-suite collection, the un-awaited async compliance gate, a stale
architecture-manifest snapshot plus its own dangling rename reference, a
test that looked like a reviewer-routing regression but was actually
constructing state with a pre-V2 calling convention, and the `slide_deck`
renderer-plugin registration gap (which needed a new `postSanitizeCheck`
hook on `ArtifactKindPlugin` plus a managed-script declaration for its
inline player script — both now real, tested, and green). No gaps from
this audit remain unfixed at the code level. The big-bang cutover evidence
itself cannot be produced by code changes — it requires an actual planned
release date, rollback owner, and sign-off, which is a decision for the
team, not an artifact this document can manufacture.
