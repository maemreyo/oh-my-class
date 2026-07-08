# Architecture & Feature Roadmap — Session 2026-06-30 (condensed 2026-07-07)

Index of roadmap ADRs and epics, with the dependency-ordered execution plan and later placement notes for newly added priorities. See `docs/system/ARCHITECTURE.md` (as-built) and `docs/system/TESTING.md` (how to test).

> Issue format: each `.scratch/<epic>/NNN-*.md` has **What to build / Acceptance criteria / Detailed test suite / Blocked by**.
> Testing policy (all epics): **real DB + real LLM** via 9router `:20228`, model `4omc` — no mocks/fakes. Deterministic logic tested without LLM; LLM-touching tests tiered per `hardening/003`.
> **2026-07-07 condensing pass**: fully-DONE, audit-confirmed-REAL epics were collapsed to one-line issue lists (implementation detail lives in git history / PR descriptions, not here). Nothing NOT-done was cut. The verbose per-wave "Verified N passed / test file names" narrative (formerly ~120 lines) was removed — it duplicated the compact wave table below and the per-epic checkmarks, and some of its ✅ marks contradicted the audit table (see footnote at execution plan). Audit table is unchanged and remains the sole ground truth where anything conflicts.

---

## ⚠️ AUDIT 2026-07-01 — false-green correction (AUTHORITATIVE)

A full code-verified audit (6 parallel auditors, checked against source, not checkmarks) found a **systemic false-green pattern**: real, unit-tested leaf modules that are **never wired into any runtime path**. Tests pass because fixtures hand-construct the intermediate contracts instead of running the prior stage. Per-unit "real DB + real LLM" is **not sufficient** — without a real-graph end-to-end run, unwired code goes green.

**The ✅ marks in the epic sections below are SUPERSEDED by this table where they conflict.** Root cause of prevention: `testing/008` canonical-flow harness (real graph, LLM boundary only stubbed) + a "no zero-caller runtime module" lint. Direction pivot: **"make the green real"** before new intelligence — see the memory note `project_next_phase_direction`.

**Corrected verdicts:**

| Area | Prior | Audited reality |
|------|-------|-----------------|
| `artifact-send-fanout/` (all 8), `agent-interaction/000,002a` | ✅ | ✅ **REAL** — the one epic wired end-to-end & tested against the real graph. `ai-001` is PARTIAL (`ArtifactWorkflowHandoff` only fires on the legacy rollback path, not the default Send path). |
| `priority-upgrades/` (all 5) | ✅ | ✅ **REAL** — model tiering, teacher memory, adaptive fast-lane, quality-flags, Anki/TSV all runtime-wired. |
| security/infra: `hardening/*`, `scaling-resilience/001,002`, `trust-lifecycle/001`, `td-001/002/003`, `testing/001,003`, `runtime-parity/002,004,006` | ✅ | ✅ **REAL**. |
| `runtime-parity/001` + `technical-debt/003` (Layer-2 quality) | ✅ | ⚠️ **PARTIAL** — gate injected but FED EMPTY DATA: `fact_check` sources always `[]` (nothing writes `metadata.research_sources`; `ResearchSource` has no body field); 3/5 pedagogical metrics unconditionally pass (no `lesson_plan` passed); **no Layer-4 G-Eval / Layer-6 in the gate**. |
| `runtime-parity/003` | ✅ | ⚠️ **PARTIAL** — legacy `/run/{id}/status` SSE still reads the old in-memory bus. |
| `runtime-parity/005` | ✅ | ⚠️ **PARTIAL** — `ExporterRegistry.export` returns hardcoded path strings (real writer lives downstream). |
| `technical-debt/002` | ✅ | ⚠️ **PARTIAL** — `stream()` skips `after_call`; MockLLMClient bypasses the runner. |
| `technical-debt/004` | ✅ | ⚠️ **PARTIAL** — Lead Agent gone, but root `docker-compose.prod.yml` still has a dangling `9router` dep. |
| **`topic-decomposition/` (units)** | ✅✅✅ | ❌ **POTEMKIN** — no runtime ever creates a `UNIT_PARENT` row. REAL: `td-001/002/003`. `td-021` sequence_critic & `td-006` unit_planner are deterministic Python, **not** the specced LLM agents. `td-005/008/009/014/015/016/017/018` = zero non-test callers (dark). `td-019` "release-gate E2E" calls `decide()`, never runs end-to-end. `td-004/007/010/011/013` = partially-wired shells whose runtime paths never fire. |
| **`vocabulary-batch/` (12)** | ✅ all | ❌ **POTEMKIN** — REAL: `vb-001/002`. Orchestrator stops at `status="queued"`; grounding→synthesis→practice→gate→export is **never chained**. `vb-004/005/006/008/010/012` = zero non-test callers. "E2E happy path" asserts the pipeline stops at `queued`. |
| **`effectiveness-loop/004,005`** | ✅ | ❌ **POTEMKIN** — `el-004` now honestly reports a local Bayesian EMA model instead of pretending pyBKT is used, but the specced pyBKT engine is still not built; `el-005` dashboard shows literal `"74%"`; mastery never reaches the planner; `record_attempt`/`mastery_for`/`decide_mastery_action` = zero non-test callers. `el-003` (capture) honestly not-done — so 004/005 run on synthetic air. |
| `scaling-resilience/003` | ✅ | ❌ **POTEMKIN** — circuit breaker & error classifier zero callers; `LLMClient.chat` never raises `TransientProviderError`; requeue unreachable. |
| `ops-observability/002` | ✅ | ❌ **POTEMKIN** — DR is row-COUNT only; no `pg_dump`/`pg_restore`. |
| `trust-lifecycle/002` | ✅ | ❌ **POTEMKIN** — `evaluate_model_drift`/`snapshot_models` zero callers; drift never triggers. |
| `testing/004` (DeepEval) | ✅ | ❌ **POTEMKIN** — metrics imported for `__name__` assertions, never `.measure()`'d; not wired into layers 2/4/6. |
| `testing/006` (promptfoo) | ✅ | ❌ **POTEMKIN** — `promptfoo.yaml` never invoked (comment only, no CI step); "security" tests are regex over constant strings. |
| `ops-observability/001,003,005` | ✅ | ⚠️ **PARTIAL** — SLO metrics real but `dispatch_slo_alerts` dead; runbooks exist but not linked from alerts; webhook inbound real but **outbound dispatch is TODO**. |
| `testing/002` | ✅ | ⚠️ **PARTIAL** — seam tests real; per-agent tests are `pytest.skip` scaffolds. |

---

## ADRs (decisions of record)

| ADR | Title | Scope |
|-----|-------|-------|
| **017** | `docs/adr/017-topic-decomposition-and-unit-fan-out.md` | Two-tier unit fan-out (parent `plan_unit` run → independent child `generate_pack` runs); stateless `UnitOrchestrator`; thin sequence + child expand; smart layers; quality tiers |
| **018** | `docs/adr/018-runtime-parity-and-legacy-decommission.md` | Close hidden capability cliffs in the authoritative stage runtime, then decommission the legacy graph and simplify sub-agents (behavior-preserving) |
| **019** | `docs/adr/019-learning-outcome-effectiveness-loop.md` | Longitudinal subsystem: Google Forms auto-capture → pyBKT knowledge tracing → mastery feeds planning + RISE template effectiveness; measures "does it teach?", not just "is it good?" |
| **020** | `docs/adr/020-langgraph-send-artifact-fanout.md` | LangGraph-native, wave-based `Send` fan-out for single-run artifact generation; reducer fan-in, per-artifact workflow states, scoped-regeneration parity, concurrency caps, and teacher-facing partial status |
| **021** | `docs/adr/021-vocabulary-batch-pipeline-mode.md` | Production `vocabulary_batch` mode inside Teaching Pack runtime; clusters as child workflow units; reusable agent capabilities; per-cluster status/evidence/export policy |
| **022** | `docs/adr/022-semantic-anchor-domain-model.md` | Semantic Anchor / Neo Tư Duy domain model; `SemanticAnchorCluster`, separate `PracticeSet`, teacher/student projections, structured edits, lexical memory |
| **040–042** | `docs/adr/04{0,1,2}-*.md` | Slide deck as first-class artifact: engine/phases (040), typed layout/block/interaction registry (041), one canonical model projected to 3 surfaces + quality gates (042) |
| **043–046** | `docs/adr/04{3,4,5,6}-*.md` | Slide deck display preferences (043), real-LLM acceptance harness (044), teaching-session foundation — stable IDs/pedagogical roles/snapshots (045), TeachingSession platform (046) |
| **047** | `docs/adr/047-slide-deck-editor-and-ai-assisted-revision.md` | Slide Deck in-browser editor + AI-assisted revision; amends SDTF-06's editing deferral |

> **Note (2026-07-07):** ADRs 040–046 and the 28 SDH/SDTF/TSP issues under `.scratch/{slide-deck-production-hardening,slide-deck-teaching-foundation,teaching-session-platform}/` were previously **absent from this roadmap** — no epic, no wave, no critical-path entry. See the new **Slide Deck track** section below, placed independently of the `td-*` critical path (no shared dependency found).

---

## Epics

> **Ground truth is the audit table above.** The ✅ marks below reflect per-issue test status at the time each issue was closed, not necessarily current feature-level reality — check the audit table first for any epic/issue named there.

### `runtime-parity/` (6) — **ALL DONE 2026-07-01**, audit-confirmed REAL *(prerequisite)*
`001` 6-layer quality gate *(⚠️ audit: PARTIAL, fed empty data)* · `002` healing→stage recovery · `003` event-bus consolidation *(⚠️ audit: legacy SSE still on old bus)* · `004` decommission legacy 18-node graph · `005` multi-format export *(⚠️ audit: hardcoded path strings)* · `006` collapse sub-agent wrappers.

### `topic-decomposition/` (21) — multi-session unit feature (ADR-017)
> ❌ **AUDIT: POTEMKIN as a feature** — no runtime creates a `UNIT_PARENT` row; fan-out is dark end-to-end. Only `td-001/002/003` are REAL. Parked pending resurrection (after vocabulary-batch). Full dependency chain kept below for whoever resumes this.
- `001`✅ Contracts+Zod codegen · `005`✅ Curriculum grounding source *(no blockers)*
- `002`✅ Unit persistence+migration *(←001)* · `003` SequenceConsistencyValidator+networkx *(←001)* · `004` Triage stage+`plan_unit` mode *(←001)*
- `013` ClassProfile+persona *(←001,002)* · `006` `unit_planner` agent *(←001,003,005 — currently deterministic Python, not the specced LLM agent)*
- `021` `sequence_critic` *(←006, deterministic not LLM)* · `008` Constrained expand+drift guard *(←001,006)* · `007` Stage wiring+UNIT_APPROVAL *(←002,006)* · `014` Decomposition memory *(←006,007)*
- `009` UnitContext *(←007,008,013)* · `015` ClassKnowledgeGraph *(←003,006,013)* · `020` Legacy approvals compat *(←007)*
- `010` UnitOrchestrator *(←002,007,009)*
- `011` Unit read API+SSE *(←001,010)* · `016` Coherence lint *(←010,011)* · `017` UnitPackager *(←010,011,parity-005)* · `018` Observability+eval *(←006,010)*
- `012` Frontend unit workspace *(←011)*
- `019` Staged rollout+E2E *(←012,016,017,018,parity-001,parity-002)* — release gate; audit: calls `decide()`, never runs end-to-end.

### `scaling-resilience/` (3) — throughput & reliability
`001`✅ Worker pool+lease-heartbeat · `002`✅ Long-lived render worker pool — both DONE 2026-06-30.
- `003` Provider-exhaustion requeue+budget degradation+circuit breaker *(←001; audit: POTEMKIN, zero callers)*

### `hardening/` (3) — **ALL DONE 2026-06-30**, audit-confirmed REAL *(independent, start anytime)*
`001` Fail-closed secrets validation · `002` Tenant-isolation+ownership-scoping audit · `003` Systemic schema-parity coverage.

### `ops-observability/` (5) — production operability
`001`✅ SLOs+alerting *(⚠️ audit: `dispatch_slo_alerts` dead)* · `002`✅ Disaster recovery *(❌ audit: POTEMKIN, row-count only, no pg_dump/restore)* · `005`✅ Webhook inbound security *(⚠️ audit: outbound dispatch TODO)* — all DONE 2026-06-30.
- `003` Runbooks per failure mode *(←001)* · `004` Per-teacher rolling cost cap+transparency *(←scaling-003)*

### `trust-lifecycle/` (4) — accessibility, model trust, teacher lifecycle, recall
`001`✅ Accessibility WCAG 2.1 AA — DONE 2026-06-30, audit-confirmed real.
- `002` Model pinning+drift detection+canary/rollback *(←testing-005; audit: POTEMKIN, zero callers)* · `003` Teacher content lifecycle — library+fork/re-edit+data portability *(←td-002)* · `004` Post-delivery content recall+incident *(←effectiveness-loop-001)*

### `effectiveness-loop/` (7) — does it actually teach? (ADR-019) *(after topic-decomp KC contracts + scaling-005)*
> ❌ **AUDIT: el-004/005 POTEMKIN** — `el-004` honestly reports a local Bayesian EMA model (no more fake pyBKT stamp), but pyBKT itself is unbuilt; `el-005` dashboard shows literal `"74%"`; mastery never reaches the planner. `el-003` (capture) honestly not-done, so the loop runs on synthetic air.
- `001` Outcome data model+`kc_ids`+privacy foundation *(←td-001)*
- `002`✅ De-stub pedagogical metrics — DONE 2026-06-30 *(no blockers)*
- `003` Google Forms delivery+response capture *(←001, scaling-005)*
- `004` pyBKT knowledge-tracing engine *(←003; audit: not built, EMA fallback only)*
- `005` Loop closure — mastery→planner+MoET export+dashboard *(←004; audit: dashboard hardcoded)*
- `006` Contrastive concept-alignment verifier (KT4EQG) *(←001)*
- `007` RISE template-effectiveness signal+3-layer HITL *(←004,005,td-014)*

### `technical-debt/` (6) — **ALL DONE 2026-07-01** (audit-corrected: 002,003,004 PARTIAL — see audit table)
`001` Consolidate onto `llm_client` · `002` Wire safety/quality middleware *(⚠️ audit: `stream()` skips `after_call`)* · `003` De-stub Layer-2 quality *(⚠️ audit: PARTIAL, same as rp-001)* · `004` Remove Lead Agent *(⚠️ audit: dangling prod-compose dep)* · `005` Config hygiene · `006` Architecture drift-guard.

### `agent-upgrades/` (7) — per-agent bespoke intelligence (none started)
- `001` **researcher** — FACT triangulation, credibility heuristics, fail-closed grounding *(←td-002)*
- `002` **planner** — staged backward-design+grounding+validator+differentiation *(←td-002,003,005)*
- `003` **content_creator** — hierarchical outline→fill + resilient degrade *(←component-002, agent-001, td-002)*
- `004` **reviewer** — revive as live Layer-4 judge, ≥2-judge robustness *(←parity-001, agent-001)*
- `005` **diagnostician** — wire into `diagnose_then_generate` *(Phase 3; ←effectiveness-004, agent-002)*
- `006` **roadmap agent** — macro milestone→unit compose+personalization *(Phase 3; ←agent-005, effectiveness-004)*
- `007` **repair+edit loop** — scoped issue-precise repair+versioned update+teacher section-editor *(←agent-003, agent-004)*

> Cross-cutting: **divide-and-conquer everywhere** — no single long master prompt; every agent decomposes into focused sub-steps.

### `agent-interaction/` (7) — how agents coordinate (native LangGraph)
⚠️ As-built: agents are **imperative calls inside stage nodes** (not graph nodes); `Command`/`Send` not used by the live runtime except via `artifact-send-fanout/`. Decision: **stage = agent's graph identity**; graph-node promotion only for narrow worker nodes like `generate_one_artifact`.
- `000`✅ Order-stable index-keyed reducer — DONE 2026-06-30
- `001`✅ Typed seam-contract layer — DONE 2026-06-30 *(⚠️ audit: `ArtifactWorkflowHandoff` only fires on the legacy rollback path, not the default Send path — PARTIAL)*
- `002a`✅ `BaseStore` substrate — DONE 2026-06-30
- `002b` `BaseStore` semantic index *(←002a + embedding-provider decision; gated/parked — LiteLLM has no embeddings route yet)*
- `003` Bounded upstream revision protocol *(←001)*
- `004a` Interaction observability — trace every handoff/revision *(←001,002a)*
- `004b` Parallel fan-out (`Send`) — artifact path superseded by `artifact-send-fanout/`; reviewer per-dimension fan-out still pending *(←000,003, agent-upgrades/004)*

> Intra-epic waves: ✅ A (done) `000`·`001`·`002a` → B `003`·`004a` → C (gated) `002b`·`004b`.

### `artifact-send-fanout/` (8) — LangGraph-native artifact generation parallelism (ADR-020) — **ALL DONE**, audit-confirmed REAL
`001` state+reducer foundation · `002` `generate_one_artifact` node · `003` wave router+fan-in · `004` scoped-regen parity · `005` concurrency+budget wiring · `006` teacher partial-status UX · `007` rollout+E2E evidence · `008` cleanup legacy imperative path.
> Order: `001→002→003→004→005→006→007→008`. Starts after `agent-interaction/000`✅; independent of unit fan-out (this is intra-run artifact fan-out).

### `vocabulary-batch/` (12) — Semantic Anchoring / Neo Tư Duy batch generator (ADR-021, ADR-022)
> ❌ **AUDIT: POTEMKIN as a feature** — orchestrator stops at `status="queued"`; grounding→synthesis→practice→gate→export never chained. Only `vb-001/002` REAL. **This is Phase 2 — the first flagship to be made real** (smallest gap, bricks exist).
- `001` Contracts+methodology mode *(no blockers)* · `002` Cluster workflow persistence *(←001)* · `003` InputNormalizer+ambiguity report *(←001)*
- `004` Researcher lexical grounding profile *(←001,003)* · `005` SemanticAnchorCluster synthesis *(←001,002,004)* · `006` PracticeGenerator capability *(←001,002)*
- `007` Vocabulary batch orchestrator *(←002,003,004,005,006 — audit: stops at queued)* · `008` Quality gate *(←005,006)*
- `009` Projections+structured editor *(←005,006,008)* · `010` Batch export package *(←007,008,009)* · `011` Teacher preferences+lexical memory *(←002,004,009)* · `012` Rollout+E2E evidence *(←010,011 — audit: E2E asserts pipeline stops at queued)*
> Order: Wave0 `001` → W1 `002,003` → W2 `004,006` → W3 `005` → W4 `007,008` → W5 `009,011` → W6 `010` → W7 `012`.

### `priority-upgrades/` (5) — **ALL DONE 2026-07-01**, audit-confirmed REAL *(independent, run parallel to any wave)*
`001` Quality flags in approval UI · `002` Per-teacher/class memory · `003` Anki-apkg/flashcard-tsv export · `004` Model tiering per task · `005` Adaptive gate fast-lane.

### `component-system/` (2) — content-component registry+smart selection (not started)
- `001` `ComponentRegistry` single source of truth *(no blockers)* · `002` Filter-then-generate *(←001)*

### `testing/` (8) — system-wide test harness
`001`✅ Harness&tiering foundation — DONE 2026-06-30, audit-confirmed real (real DB+LLM, `@pytest.mark.real_llm`, no fake-LLM).
- `002` Three-layer pyramid *(←001; ⚠️ audit: PARTIAL, per-agent tests are skip-scaffolds)*
- `003` Deterministic trajectory+control-flow gates *(←001; audit: REAL)*
- `004` DeepEval quality metrics→Layers 2/4/6 *(←001,parity-001; ❌ audit: POTEMKIN, never `.measure()`'d)*
- `005` Golden dataset+nightly regression *(←004)*
- `006` Promptfoo security/red-team *(←001; ❌ audit: POTEMKIN, yaml never invoked)*
- `007` Chaos/fault-injection *(←001,parity-002,scaling-003)*
- `008` **Canonical flow harness** — shared scenarios, real-graph conformance, `make e2e` *(←001 — this is the fix for the whole false-green pattern above)*

---

## Slide Deck track (added 2026-07-07, filled in same day after a 50-question design interview — independent of the `td-*` critical path)

48 issues across 5 sub-tracks, each parented to an ADR, currently `status: ready-for-agent`/Proposed, **zero implemented**:

- **`slide-deck-production-hardening/` (SDH-01..12, ADR-043/044)** — display preferences, student-safe chrome, print fidelity, density guards, real-LLM harness, backward-compat, observability, sanitizer hardening.
- **`slide-deck-teaching-foundation/` (SDTF-01..08, ADR-045)** — stable IDs, pedagogical roles/pacing, related-artifact refs, student companion view, differentiation, immutable snapshots/remix lineage, component-registry alignment. SDTF-03 carries a forward note for a future (not-yet-filed) worksheet-companion feature.
- **`teaching-session-platform/` (TSP-01..09, ADR-046)** — session lifecycle/privacy/retention (TSP-01), join+role tokens/room-code/roster (TSP-02), event log/Redis-SSE/recovery/offline-degradation (TSP-03), live cockpit incl. ephemeral annotation + opt-in pacing nudge (TSP-04), response collection incl. non-competitive gamification + capture-only analytics (TSP-05), precomputed-first branching + AI-rewrite-pipeline reuse (TSP-06), delivery modes — v1 `live`-only, schema reserves all 5 (TSP-07), harness (TSP-08), **new:** teacher-mediated class recap (TSP-09). All TSP-01..07 amended 2026-07-07 with concrete mechanics from the design interview; ADR-046 itself amended with the same decisions (see its "Amendment" section).
- **`slide-deck-editor/` (SDE-01..11, ADR-047 — new)** — real schema-bound LLM call in `ContentMaterializer` (SDE-01), full 21-layout/block/interaction registry contract (SDE-02), structured-visual block editor — no freeform WYSIWYG (SDE-03), dual-path edit API + snapshot versioning + optimistic locking (SDE-04), linear version history + restore (SDE-05), versioned exports + staleness indicator (SDE-06), editor route + local-draft-then-commit save (SDE-07), block-scoped AI-rewrite with teacher confirmation (SDE-08), real-LLM harness extension (SDE-09), feature flags + AI-rewrite rate limit (SDE-10), lightweight success observability (SDE-11). Amends ADR-045/SDTF-06's editing deferral.
- **`slide-deck-features/` (SDX-01..06, various parents)** — bilingual EN↔VI translation (SDX-01, parent ADR-047) · teacher-scoped media asset library (SDX-02, interim scope ahead of future `trust-lifecycle/003`) · system template presets (SDX-03, parent ADR-047) · AI-generated alt-text (SDX-04, parent ADR-047 + `trust-lifecycle/001`) · PPTX export only, no import (SDX-05, parent ADR-042) · runs-list search/filter (SDX-06, **no slide-deck parent** — general app UX, filed here because SDX-02/03 make the gap acute sooner).

**Slide Deck track dependency order:** `SDH-01/02/06` and `SDTF-01` are the unblocked entry points most other slide-deck issues cite as `blocked by`. `SDE-01→02→03→04→{05,06}→07→08→{09,10,11}` is the editor's internal chain; `SDE-03` additionally needs `SDTF-01` (stable block IDs) — this is the track's one real cross-sub-track dependency, matching the "merge at SDTF-01" decision from the design interview. `SDX-02` needs `SDE-03`; `SDX-04` needs `SDE-01`+`SDX-02`; `SDX-01`/`SDX-03`/`SDX-05` only need `SDE-01`/`SDE-02`. `TSP-09` needs `TSP-01`+`TSP-05`+`TSP-07`. `SDX-06` is unblocked.

**Explicitly not blocked on (by design, mirror-shape-now-consolidate-later per the interview):** `OPS-07` (data lifecycle/retention — TSP-01 builds its own session-scoped predicate now), `PRIV-01` (K-12 compliance mapping — TSP-01 writes its own addendum now), `organization_id` schema gap (SDE-04 inherits the fix automatically when it lands, needs no slide-deck code), `ops-observability/004` (cost cap — SDE-10 ships a self-contained rate limit instead), `effectiveness-loop` (TSP-05 ships real capture only, no dashboard), `trust-lifecycle/003` (SDX-02 ships a minimal version now, shaped to be absorbed later).

> No shared dependency found between this track and `td-*`/`vb-*`/`el-*` — runs fully in parallel.

---

## Execution plan (dependency-ordered waves) — `td-*` / `priority-upgrades` / `artifact-send-fanout` / `vocabulary-batch` track only

Original topological order of **56 `td`-prefixed-epic issues** across 8 epics, plus `priority-upgrades/` (5) and `artifact-send-fanout/` (8) = **81 tracked issues total** for this track. Run everything in a wave in parallel; a wave starts when all its blockers (earlier waves) are done.

> **Wave ✅ marks below are per-issue test status only — several were corrected by the audit table above** (this pass removed stale ✅ marks for `te-002`, `te-004`, `te-006` that contradicted the audit's PARTIAL/POTEMKIN verdicts for those exact IDs; everything else left as originally recorded). If a wave/epic disagree, the audit table wins.

**Epic prefixes:** `td`=topic-decomposition · `sr`=scaling-resilience · `hd`=hardening · `te`=testing · `el`=effectiveness-loop · `ops`=ops-observability · `tl`=trust-lifecycle · `rp`=runtime-parity (done) · `pu`=priority-upgrades · `asf`=artifact-send-fanout.

| Wave | Issues (count) | Theme | Status |
|------|----------------|-------|--------|
| **0 (13)** | `td-001,005` · `sr-001,002` · `hd-001,002,003` · `te-001` · `el-002` · `ops-001,002,005` · `tl-001` | Contracts+grounding · render/worker pool · secrets/authz/schema-parity · harness · de-stub pedagogical · SLO/DR/webhook · a11y | ✅ done 2026-06-30 |
| **1 (10)** | `td-002,003,004` · `sr-003` · `te-002,003,004,006` · `el-001` · `ops-003` | Persistence/validator/triage · provider-resilience · pyramid/trajectory/quality-metrics/security · outcome-model · runbooks | done, but `te-002` PARTIAL / `te-004,006` POTEMKIN per audit |
| **2 (9)** | `td-006,013` · `te-005,007` · `el-003,006` · `ops-004` · `tl-003,004` | unit_planner · persona · golden-dataset/chaos · Forms-capture/concept-verifier · cost-cap · content-lifecycle · recall | pending |
| **3 (6)** | `td-007,008,015,021` · `el-004` · `tl-002` | stage-wiring/gate · expand+drift · knowledge-graph · sequence-critic · BKT engine · model-drift | done, `el-004` POTEMKIN per audit |
| **4 (4)** | `td-009,014,020` · `el-005` | UnitContext · decomposition-memory · approvals-compat · loop-closure+MoET | done, `el-005` POTEMKIN per audit |
| **5 (2)** | `td-010` · `el-007` | UnitOrchestrator (fan-out) · RISE template-effectiveness | done |
| **6 (2)** | `td-011,018` | Unit read API/SSE · observability+eval | done |
| **7 (3)** | `td-012,016,017` | Frontend workspace · coherence lint · UnitPackager | done |
| **8 (1)** | `td-019` | Staged rollout+E2E (release gate) | done per-issue, but ❌ POTEMKIN feature-level per audit — **not actually release-ready** |

**`artifact-send-fanout/`** placement: `asf-001` W1-level → `asf-002` W2 → `asf-003` W3 → `asf-004`+`asf-005` W4 → `asf-006` W5 → `asf-007` W6 → `asf-008` W7 cleanup. All done, audit-confirmed real.

**`priority-upgrades/`** placement: `pu-004` W0 (no blockers) → `pu-001,002,003` W1 → `pu-005` W2. All done, audit-confirmed real.

**`vocabulary-batch/`** placement: `vb-001` W0 → `vb-002,003` W1 → `vb-004,006` W2 → `vb-005` W3 → `vb-007,008` W4 → `vb-009,011` W5 → `vb-010` W6 → `vb-012` W7. All marked done per-issue, but ❌ POTEMKIN feature-level per audit — orchestrator stops at `queued`.

### Cross-epic gates
`td-019` ← `rp-001`+`rp-002` · `td-017` ← `rp-005` · `td-010/011` ← `rp-003` · `te-004` ← `rp-001` · `te-007` ← `rp-002`+`sr-003` · `el-003` ← `el-001`+`rp-005` · `el-007` ← `el-004,005,td-014` · `tl-002` ← `te-005` · `tl-003` ← `td-002` · `tl-004` ← `el-001` · `ops-004` ← `sr-003`.

### Critical path (longest chain → release)
`td-001 → td-002 → td-007 → td-009 → td-010 → td-011 → {td-016, td-017} → td-012 → td-019` (8 waves) — **per-issue complete, but audit shows the feature itself is dark (POTEMKIN)**, so this critical path is not actually cleared for release. The effectiveness-loop's longest chain `td-001 → el-001 → el-003 → el-004 → el-005 → el-007` (5 waves) runs in parallel and does not gate the unit release.

### Production-readiness gate (must land before real-classroom exposure)
`hd-001` secrets · `tl-001` a11y · `ops-001` SLO/alerting · `ops-002` DR *(❌ audit: POTEMKIN)* · `ops-005` webhook security · `tl-004` recall — all Wave 0–2, so nominally early, but `ops-002` needs real work per audit before this gate is actually satisfied.

---

## Testing stack — verdict (from the AI-agent-testing framework research)

**Adopt:** DeepEval (pytest metrics, **9router-backed `4omc`, offline/no-egress**) · **Langfuse** (self-hosted — tracing/eval/dataset/annotation/trace-feedback) · Promptfoo (K-12 red-team + INVARIANT-05/06). **Reject:** LangSmith (proprietary, no self-host, K-12 data egress) · fake-LLM (violates real-test policy) · Lead-Agent-delegation trajectory (not in the authoritative stage runtime) · agentverify (N/A here).

Patterns kept: three-layer pyramid, golden dataset, semantic/trajectory-over-exact-match, health gates, chaos/fault-injection, production-trace feedback. `testing/` is the **harness layer**; per-feature epics' suites run on it.

**Real-LLM release gate (added 2026-07-08, from the real-LLM-integration design interview):** `.github/workflows/real-llm-release-gate.yml` runs `@pytest.mark.real_llm` against live 9router (`:20228`, `4omc`) on a **self-hosted runner, `workflow_dispatch`-only** — 9Router currently runs unconfigured/manual on a personal machine, not containerized, so a self-hosted runner is the only way CI can reach `localhost:20228` today, and `workflow_dispatch` (not `schedule:` cron) is used because a self-hosted runner only fires when its host machine happens to be online. **TODO — not yet done:** containerize 9Router (service container + provider credentials in repo secrets) so this can run on a normal GitHub-hosted runner with a true unattended nightly `schedule:` trigger, instead of manual-dispatch-only on a personal machine.

## Principles baked into every issue
- **Divide-and-conquer everywhere; no single long master prompt** — every agent decomposes into focused sub-steps.
- **New stage runtime only** (`teaching_pack/graph.py`); legacy `build_oh_my_class_graph` frozen, not extended.
- **Reuse existing ports/adapters** (`QualityGate`, `render()`, `ExporterRegistry`, gate registry, JobStore, `eligible_at` requeue, idempotency keys).
- **Fail-closed**, never silent downgrade. **Computed-not-materialized** unit state; `RunStatus` unchanged.
- **Idempotent + durable-substrate** orchestration (JobStore + DB are truth; in-memory events are SSE-only).
- **Simplify = modern only, zero feature loss** (capability inventory + golden parity before deleting).
- **Backward-compatible** migrations (nullable columns); single-lesson flow zero-regression.
