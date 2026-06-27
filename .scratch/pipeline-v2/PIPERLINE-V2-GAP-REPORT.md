# Pipeline V2 — Comprehensive Gap Report

> **Audit date**: 2026-06-27
> **Branch state**: 151 staged files (~19.5k insertions), uncommitted
> **Method**: 4 parallel deep reviewers + orchestrator reconciliation against codebase
> **Scope**: ISSUE-001 through ISSUE-015

---

## Summary Verdict

| Issue | Title | Status | Verified | Partial | Missing |
|-------|-------|--------|----------|---------|---------|
| 001 | Foundation Architecture | PARTIAL | Stage graph, config, boundaries | Ports incomplete (no LLM/search/renderer) | — |
| 002 | Production Persistence | PARTIAL | Migrations, stores, checkpointer | No process-restart recovery proof | Full multi-process production recovery |
| 003 | Control Plane/Executor | PARTIAL | Routes, gate registry, worker, status machine | Live streaming (only replay), sweeper wiring | — |
| 004 | RunContract/Setup | PARTIAL | Contract model, preflight, gate payloads | Monotonic revision enforcement, edit→revision wiring | — |
| 005 | Research Engine | PARTIAL | Contracts, planning, ranking, safety, gate | Sequential fetch (not parallel), no cache, no config-driven classifier | Live 9Router tests, LLM-assisted planning |
| 006 | Adaptive LLM Transport | PARTIAL | Transport policy, prompt gate, metadata | Thresholds hardcoded, 2/4 JSON strategies, no Langfuse-down test | Live 9Router smoke tests |
| 007 | Artifact Workflow | PARTIAL | Orchestrator, bounded parallelism, retry, quality validation | Error classification limited, no scoped rejection routing | Section-level splitting, live 9Router generation |
| 008 | Rendered Preview/Approval | PARTIAL | Snapshot store, APIs, hash validation, standalone check | Student preview is stub (not Eta), no renderer integration test | Browser/manual QA, version mismatch blocking |
| 009 | Quality/Healing/Safety | PARTIAL | Deterministic gates, export readiness, safety gates, failure classifier | Healing only classifier (no executors), no scoped backend routing | Adaptive LLM judge, pack coherence, healing executors |
| 010 | UI/UX Cutover | PARTIAL | Hooks, stage progress, artifact progress, scoped rejection | SSE reconnect missing, gate bodies JSON-oriented, preview no toggle | Browser QA, a11y, full teacher journey |
| 011 | E2E Release Gates | PARTIAL | Deterministic E2E suite, release evidence infra, Postgres fixtures | Privacy tests partial | Live 9Router tests, evidence report on disk, Langfuse-degradation, SSE tests |
| 012 | Auth/Governance | PARTIAL | Auth model, ownership, retention, soft-delete, identity hash, schema versioning | Generated frontend type drift enforcement not proven | Previous-version adapter, end-to-end student evidence TTL |
| 013 | Operations Hardening | PARTIAL | Idempotency, job leases, backpressure, worker, sweeper functions | Budget in-memory only, sweeper not wired periodically, no queued status | Budget DB persistence, crash timing proof, live timeout/degrade |
| 014 | Notifications/Admin Recovery | PARTIAL | Notification models, in-app channel, recovery actions, audit trail | Only 3/9 emit helpers, no admin list endpoint | Admin list/filter endpoint, RETRY_NOTIFICATION action |
| 015 | Prompt/Template Governance | PARTIAL | Prompt/template/theme registries, drift detection, seed data | Drift detection not enforced in CI, no overlay system | Prompt compiler, eval harness, rubric registry, repair prompts |

---

## Gap Category 1: Live 9Router Integration (Critical — Blocks Production Readiness)

This is the single largest gap across the entire project. The codebase contains extensive unit/integration tests with mocks, but **zero live 9Router traffic evidence**.

### Affected Issues

| Issue | Required Scenario | Current State |
|-------|-------------------|---------------|
| **005** Research Engine | Live search/fetch for Math, English, Science | All tests use fake providers. Sequential fetch loop. No live queries recorded. |
| **006** LLM Transport | Long streamed call, short non-streamed, timeout-to-stream fallback | All tests mock transport. No live 9Router smoke evidence. |
| **007** Artifact Workflow | Lesson/worksheet/quiz/recap generation via live 9Router | All generation tests use a stub `ArtifactGenerator` protocol. No live artifact output recorded. |
| **011** E2E Release Gates | 9 specific live scenarios (Vietnamese Math, English ESL, Science, clarification, contract confirmation, search confirmation, scoped rejection, timeout/healing, standalone export) | E2E conftest documents "LLM calls are mocked at the store level — no real API traffic." |

### Impact

Without live 9Router evidence, no issue can claim full completion. The entire release gate (Issue 011) depends on this. The staged code has strong deterministic coverage but does not prove production-path behavior.

---

## Gap Category 2: Renderer Integration (Blocks Visual Approval)

### ISSUE-008 — Student preview is a text-stripping stub

```
pipeline_v2_snapshot_store.py:174-183 — render_student_preview_html()
```

This function concatenates section text with basic `<section>` tags. It does **not** invoke the Eta template renderer (`packages/renderer/`). The actual teaching pack HTML layout, CSS theming, print styles, and responsive design are not exercised by the preview path.

### What's missing

1. **No Eta renderer integration** in the snapshot creation pipeline — the renderer package exists (`packages/renderer/`) with templates, but it's not wired into the gateway snapshot flow
2. **No renderer integration test** that proves templates actually produce standalone HTML from `ArtifactContent` JSON
3. **No version mismatch blocking** — renderer/template/theme version columns exist on the snapshot model but no code rejects snapshots from mismatched versions

---

## Gap Category 3: SSE Live Streaming (Blocks Real-Time UX)

### Frontend: No reconnect/replay on `EventSource`

```
apps/web/src/hooks/use-pipeline-v2.ts:113-128
```

The `EventSource` opens a subscription but has no `onerror` handler, no reconnect logic, and no `Last-Event-ID` header on reconnection. On page refresh, `v2Events` resets to `[]`.

### Backend: Only replay, no live push

```
services/gateway/routers/pipeline_v2_runs.py:276-299
```

The SSE endpoint replays persisted events after `Last-Event-ID` and then holds the connection open. There is no mechanism to push new events to connected clients as they occur (no WebSocket, no polling, no event bus).

### Impact

Teachers see stale state after page refresh. Gate notifications, stage transitions, and artifact progress require manual refresh until the next SSE message arrives (if any).

---

## Gap Category 4: Healing Execution (Blocks Quality Assurance)

### ISSUE-009 — Classifier exists, executors don't

The healing system has:

| Component | Status | Location |
|-----------|--------|----------|
| Failure classifier | ✅ Implemented | `quality_gates.py:116-133` — 9 failure classes → 7 strategies |
| Healing decision | ✅ Implemented | `HealingDecision` dataclass with `max_attempts` |
| Per-artifact retry | ✅ Implemented | `artifact_workflow.py:142-155` — bounded loop |
| Schema repair executor | ❌ Missing | No code that actually repairs malformed JSON |
| Answer-key repair executor | ❌ Missing | No code that moves/removes teacher-only data |
| PII removal executor | ❌ Missing | No code that strips PII from generated content |
| Presentation repair executor | ❌ Missing | No code that fixes accessibility/external assets |
| Factual uncertainty routing | ❌ Missing | No code that routes to research enrichment |
| Pedagogical mismatch routing | ❌ Missing | No code that decides artifact-only vs blueprint-level |
| Pack-level coherence check | ❌ Missing | No cross-artifact consistency validation |

### What exists vs what's needed

The `quality_workflow.py` emits quality events and checks export readiness, but there's no `healing_loop()` function that takes a failed artifact, applies the classified strategy, re-generates, and re-validates. The current retry loop in `artifact_workflow.py` just re-runs the same generator — it doesn't apply repair-specific prompts or transformations.

---

## Gap Category 5: Adaptive LLM Judge (Blocks Content Quality)

### ISSUE-009 — No adaptive judge implementation

The issue requires:

1. **Risk-tier selection** (borderline/rigorous) based on artifact type, subject, locale
2. **Artifact-type-aware judge routing** with different rubrics per artifact
3. **Versioned rubric registry** composing base + artifact + subject + locale criteria

Current state: zero grep matches for `adaptive|risk_mode|borderline|rigorous|G.Eval|geval|rubric` in `services/gateway/`. The reviewer agent (Issue 009) confirmed this is entirely absent.

The `content-fusion` model route exists in the LLM config (AGENTS.md §6.1.1) but no code routes artifact evaluation through it.

---

## Gap Category 6: Prompt/Template Governance (Blocks Controlled Evolution)

### ISSUE-015 — Registry exists, governance doesn't

| Sub-feature | Status | Detail |
|-------------|--------|--------|
| Prompt registry with hash validation | ✅ | `packages/agents/prompts/registry.py` — semver + SHA-256 |
| Template/theme registries | ✅ | `packages/renderer/templates/registry.py`, `common/branding/registry.py` |
| Drift detection | ✅ | `packages/agents/prompts/drift.py` — detects mismatches |
| Drift enforcement (CI/startup fail) | ❌ | Detection only. No test fails on drift. No startup check. |
| Prompt section compiler | ❌ | No compaction logic. No section-level prompt assembly. |
| Safe compaction | ❌ | No example-dropping-before-core logic. |
| Structured-output strategy routing | ❌ | `PromptModule.output_schema` exists but no per-task strategy selector. |
| Prompt eval harness | ❌ | No static compile tests, schema eval, regression corpus, or live eval. |
| Base + locale/subject/artifact overlays | ❌ | Seed modules have hardcoded metadata. No overlay composition mechanism. |
| Per-failure-type repair prompts | ❌ | Single `REPAIR_V1` prompt. No format/content/accessibility-specific repair prompts. |
| Versioned rubric registry | ❌ | Zero grep matches. No rubric system exists. |

---

## Gap Category 7: Background Task Wiring (Blocks Production Operations)

### ISSUE-013 — Recovery sweeper not wired

```
services/gateway/recovery_sweeper.py — sweep_stuck_jobs(), sweep_escalated_gates()
services/gateway/main.py — lifespan function has no sweeper integration
```

The sweeper functions exist and have tests, but `main.py`'s lifespan does not start a periodic background task. In production, stuck jobs and escalated gates would never be automatically swept.

### ISSUE-013 — Budget ledger is in-memory only

```
services/gateway/budget.py — "Pure in-memory dataclasses — no DB persistence"
```

`BudgetLedger` tracks usage per run but survives only in the process memory. After restart, all budget state is lost. The issue requires DB-persisted budget ledger/event records.

---

## Gap Category 8: Queue/Backpressure Status (Blocks Graceful Degradation)

### ISSUE-013 — Backpressure rejects, never queues

```
services/gateway/backpressure.py — check_backpressure() returns allowed=True/False
```

When a teacher hits the active-run limit, the create-run request is **rejected** with an error. The issue requires:

1. A `QUEUED` or `DELAYED` status in the `RunStatus` enum
2. A queueing mechanism that holds requests and processes them when capacity opens
3. UI-visible delayed/queued state so teachers know their request is pending

Currently, `RunStatus` has: `PENDING, PLANNING, RESEARCHING, GENERATING, RENDERING, REVIEWING, EXPORTING, AWAITING_APPROVAL, COMPLETED, FAILED, CANCELLED, ESCALATED, TIMED_OUT`. No queued/delayed state exists.

---

## Gap Category 9: Admin Operations (Blocks Operator Tooling)

### ISSUE-014 — No admin list/filter endpoint

The notification router (`routers/notifications.py`) has:

- `GET /admin/runs/{run_id}/summary` — single-run summary
- `POST /admin/runs/{run_id}/recover` — recovery action

What's missing:

- `GET /admin/runs?status=failed&status=stuck` — list/filter endpoint
- Pagination, sorting, and filtering by status, time range, teacher

### ISSUE-014 — Incomplete notification emission

Of the 9 notification event types defined in `notification_models.py`:

| Event Type | Has Emit Helper? |
|------------|-----------------|
| `clarification_required` | ✅ `notify_gate_required()` |
| `contract_confirmation` | ❌ |
| `search_confirmation` | ❌ |
| `blueprint_ready` | ❌ |
| `content_preview_ready` | ❌ |
| `run_completed` | ✅ `notify_run_completed()` |
| `run_failed` | ✅ `notify_run_failed()` |
| `run_escalated` | ❌ |
| `gate_timeout_warning` | ❌ |

---

## Gap Category 10: Auth/Governance End-to-End (Blocks Multi-Tenant Production)

### ISSUE-012 — Schema versioning is 1.0-only

```
services/gateway/schema_version.py — SUPPORTED_VERSIONS = frozenset({"1.0"})
```

The `migrate_contract()` function handles 1.0→1.0 (no-op). There is no previous-version adapter, no migration logic, and no test for reading an older schema version. The issue requires "read adapters for previous V2 versions."

### ISSUE-012 — Generated frontend type drift not enforced

The issue requires "generated or mechanically checked frontend API types from backend OpenAPI/contracts." The staged changes include frontend components that consume V2 APIs, but no CI step or script generates Zod/TypeScript types from backend Pydantic models or OpenAPI spec.

### ISSUE-012 — Student evidence TTL enforcement end-to-end

Retention config exists (`retention.py` — student_evidence: 30 days). The `purge_student_evidence()` function exists. But the full pipeline path from student evidence ingestion → minimization → storage → TTL expiry → purge was not verified end-to-end.

---

## Gap Category 11: Frontend Quality (Blocks Teacher Experience)

### ISSUE-010 — Gate bodies are JSON dumps

The gate shell (`pipeline-v2-gate-shell.tsx`) renders:

- **Search plan confirmation**: raw JSON (`JSON.stringify(searchPlan)`)
- **Blueprint approval**: `ReadableObject` component (key-value rendering of raw object)
- Only **content approval** has a structured UI (artifact tabs, preview, rejection)

### ISSUE-010 — No student/teacher preview toggle

`snapshotPreviewUrl()` supports both `"student"` and `"teacher"` query params, but the `ContentSnapshots` component hardcodes `view="student"`. No toggle or tab UI exists.

### ISSUE-010 — Missing loading/error states

- Loading: bare "Loading..." text (no skeleton/spinner)
- Error: `<pre>` block with raw error (no retry button)
- 404: not handled for non-existent runs

---

## Gap Category 12: Port/Interface Architecture (Blocks Clean Dependency Injection)

### ISSUE-001 — Missing ports in package-level module

`packages/agents/pipeline_v2/ports.py` defines 4 protocols:

| Port | Status |
|------|--------|
| `RunStore` | ✅ |
| `EventWriter` | ✅ |
| `ArtifactSnapshotStore` | ✅ |
| `RunExecutor` | ✅ |
| LLM Transport | ❌ Missing |
| Search/Fetch Client | ❌ Missing |
| Renderer | ❌ Missing |
| Notification Channel | ❌ Missing |
| Quality Gate | ❌ Missing |

The `PipelineV2Graph` protocol is defined in `services/gateway/pipeline_v2_executor.py` instead of in `ports.py`, splitting the interface definitions across packages and services.

---

## Gap Category 13: Contract/Control Plane Wiring (Blocks Edit Flow)

### ISSUE-004 — Teacher edit→revision not wired

The generic resume route (`routers/pipeline_v2_runs.py`) stores the gate response and enqueues a job. But when that job executes:

- The graph receives `Command(resume={"action": "edit", "edits": {...}})` 
- No code in the pipeline nodes applies the edits to the `RunContract`
- `PipelineV2ControlStore.revise_contract()` exists but is not called from the resume execution path

### ISSUE-003 — Cancel lacks actor/reason in event

```
routers/pipeline_v2_runs.py:239-273
```

The cancel endpoint writes a `pipeline_v2.run.cancelled` event, but the payload only contains `{"cancelled_jobs": N}`. The issue requires actor (who cancelled) and reason (why) to be persisted.

### ISSUE-005 — Research cache missing

The issue requires "research cache respects TTL and does not leak between tenants." No cache implementation exists in the research engine code path. Every search/fetch is a fresh call.

---

## Gap Category 14: Browser/Manual QA (Blocks Visual Verification)

### Affected Issues

| Issue | Required QA | Found |
|-------|-------------|-------|
| **008** Rendered Preview | Browser QA for approval preview, narrow viewport, print preview, iframe sandbox | None |
| **010** UI/UX Cutover | Browser QA for complete teacher journey | None |
| **010** UI/UX Cutover | Accessibility checks for modal focus, labels, keyboard actions | None |
| **010** UI/UX Cutover | Responsive tests for mobile-ish viewport on gate dialogs | None |

---

## Gap Category 15: Release Evidence (Blocks Production Claim)

### ISSUE-011 — No evidence report on disk

The issue requires a release evidence report under `docs/reports/` or `.scratch/pipeline-v2/artifacts/`. Neither directory contains a V2 evidence report. The `release_evidence.py` module has `generate_evidence()` that can produce one, but no report has been generated and persisted.

### ISSUE-011 — E2E fixture documents mocked behavior

```
tests/e2e/conftest.py:1-6
"LLM calls are mocked at the store level — no real API traffic."
```

The deterministic E2E suite is valuable for regression testing but does not satisfy the "live 9Router release matrix" requirement.

---

## Priority Ranking for Production Readiness

| Priority | Gap Category | Blocking Issues | Effort Estimate |
|----------|-------------|-----------------|-----------------|
| **P0** | Live 9Router integration tests | 005, 006, 007, 011 | High — requires real API keys, scenario design, evidence collection |
| **P0** | Renderer integration (Eta→snapshot) | 008, 010 | Medium — wire renderer into snapshot creation path |
| **P0** | Healing executors | 009 | High — 5+ repair strategies need implementation |
| **P0** | Release evidence report generation | 011 | Low — module exists, just needs execution |
| **P1** | SSE live streaming | 003, 010 | Medium — event bus or polling mechanism needed |
| **P1** | Prompt compiler + eval harness | 015 | High — new subsystem |
| **P1** | Adaptive LLM judge + rubric registry | 009, 015 | High — new subsystem |
| **P1** | Recovery sweeper periodic wiring | 013 | Low — add BackgroundTask to lifespan |
| **P1** | Budget DB persistence | 013 | Medium — new table + migration |
| **P1** | Admin list/filter endpoint | 014 | Low — single new route |
| **P1** | Queue/delayed status for backpressure | 013 | Medium — new status + queueing mechanism |
| **P2** | Frontend gate body structured views | 010 | Medium — search/blueprint need teacher-friendly UI |
| **P2** | Prompt overlays + repair prompts | 015 | Medium — composition system |
| **P2** | SSE reconnect on frontend | 010 | Low — add `onerror` + `Last-Event-ID` |
| **P2** | Notification emit helpers (6 missing) | 014 | Low — one function per type |
| **P2** | Contract edit→revision wiring | 004 | Medium — resume execution path needs revision logic |
| **P2** | Generated frontend type drift enforcement | 012 | Medium — CI script + Zod generation |
| **P3** | Pack-level coherence check | 009 | High — cross-artifact consistency logic |
| **P3** | Research cache with TTL | 005 | Low — in-memory TTL dict |
| **P3** | Section-level artifact splitting | 007 | High — recursive generation strategy |
| **P3** | Browser/manual QA evidence | 008, 010 | Medium — requires manual execution |
| **P3** | Previous-version schema adapter | 012 | Low — add migration function |

---

## Conclusion

The Pipeline V2 codebase has **substantial implementation** across all 15 issues — 151 staged files with ~19.5k insertions covering persistence, control plane, research, transport, artifact workflow, quality gates, auth, operations, notifications, and governance. The deterministic test suite is extensive (453+ test functions across 36+ test files).

However, the original report's "all issues complete" claim is **not accurate**. Every issue has verifiable gaps. The most critical are:

1. **Zero live 9Router evidence** — the system has never been tested against real providers
2. **Renderer not wired** into the snapshot/approval pipeline — teachers would see raw text, not designed teaching packs
3. **Healing is classification only** — failed artifacts get retried, not repaired
4. **SSE is replay-only** — no real-time updates to connected clients
5. **Prompt governance is registry-only** — no compiler, no eval, no rubric, no enforcement

None of these are "just needs testing" gaps. They are **implementation gaps** requiring new code, not just verification of existing code.
