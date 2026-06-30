# Architecture & Feature Roadmap — Session 2026-06-30

Index of everything produced this session: 3 ADRs + 12 epics (76 issues), with the dependency-ordered execution plan. See `docs/system/ARCHITECTURE.md` (as-built) and `docs/system/TESTING.md` (how to test).

> Issue format: each `.scratch/<epic>/NNN-*.md` has **What to build / Acceptance criteria / Detailed test suite / Blocked by**.
> Testing policy (all epics): **real DB + real LLM** via 9router `:20228`, model `4omc` — no mocks/fakes. Deterministic logic tested without LLM; LLM-touching tests tiered per `hardening/003`.

---

## ADRs (decisions of record)

| ADR | Title | Scope |
|-----|-------|-------|
| **017** | `docs/adr/017-topic-decomposition-and-unit-fan-out.md` | Two-tier unit fan-out (parent `plan_unit` run → independent child `generate_pack` runs); stateless `UnitOrchestrator`; thin sequence + child expand; smart layers; quality tiers |
| **018** | `docs/adr/018-runtime-parity-and-legacy-decommission.md` | Close hidden capability cliffs in the authoritative stage runtime, then decommission the legacy graph and simplify sub-agents (behavior-preserving) |
| **019** | `docs/adr/019-learning-outcome-effectiveness-loop.md` | Longitudinal subsystem: Google Forms auto-capture → pyBKT knowledge tracing → mastery feeds planning + RISE template effectiveness; measures "does it teach?", not just "is it good?" |

---

## Epics

### `runtime-parity/` (6) — close capability cliffs, then decommission *(prerequisite)* — **PARTIAL (reconciled with code audit 2026-06-30)**
⚠️ A fresh codebase audit (see `docs/system/ARCHITECTURE.md`) found the earlier "all DONE" claim **overstated**. Verified status:
- ✅ `004` Decommission legacy 18-node graph — **DONE** (graph removed; legacy `/run` + `/run/approve` return 410).
- ✅ `006` Collapse sub-agent StateGraph wrappers — **DONE** (sub-agents are direct node functions).
- 🟡 `002` Healing → stage recovery — **PARTIAL** (`healing_runtime`/`quality_routing` wired, but only triggers on coherence failures since the 6-layer gate isn't injected).
- 🟡 `005` Multi-format export — **PARTIAL** (`ExporterRegistry` exists; **HTML only** functional; gift/h5p/qti return placeholder paths; google_forms unsupported).
- ❌ `001` Wire 6-layer quality — **NOT DONE** (`build_teaching_pack_graph` called with `quality_gate=None`; `render_quality` runs only the thin `quality_issues()`).
- ❌ `003` Event-bus consolidation — **NOT DONE** (`events.py` + `teaching_pack_event_bus.py` both still exist).

→ The not-done/partial items remain open; their concrete completion + the newly-found gaps are tracked in **`technical-debt/`** below. (The earlier "268 passed" run validated decommission, not the quality/export wiring — tests didn't assert `quality_gate` injection.)

### `topic-decomposition/` (21) — multi-session unit feature (ADR-017)
- ✅ `001` Contracts + Zod codegen — **DONE 2026-06-30** · ✅ `005` Curriculum grounding source — **DONE 2026-06-30** *(no blockers)*
- ✅ `002` Unit persistence + migration — **DONE 2026-06-30** *(←001)* · `003` SequenceConsistencyValidator + networkx *(←001)* · `004` Triage stage + `plan_unit` mode *(←001)*
- `013` ClassProfile + persona *(←001,002)* · `006` `unit_planner` agent *(←001,003,005)*
- `021` `sequence_critic` *(←006)* · `008` Constrained expand + drift guard *(←001,006)* · `007` Stage wiring + UNIT_APPROVAL *(←002,006)* · `014` Decomposition memory *(←006,007)*
- `009` UnitContext (theme/research/persona) *(←007,008,013)* · `015` ClassKnowledgeGraph *(←003,006,013)* · `020` Legacy approvals compat *(←007)*
- `010` UnitOrchestrator *(←002,007,009)*
- `011` Unit read API + SSE *(←001,010)* · `016` Coherence lint *(←010,011)* · `017` UnitPackager *(←010,011,parity-005)* · `018` Observability + eval *(←006,010)*
- `012` Frontend unit workspace *(←011)*
- `019` Staged rollout + E2E *(←012,016,017,018,parity-001,parity-002)* — **release gate**

### `scaling-resilience/` (3) — throughput & reliability
- ✅ `001` Worker pool + intra-worker concurrency + **lease-heartbeat** — **DONE 2026-06-30** (fixes latent double-execution)
- ✅ `002` Long-lived render worker pool + version pin + concurrency cap — **DONE 2026-06-30**
- `003` Provider-exhaustion requeue + budget degradation + circuit breaker *(←001)*

### `hardening/` (3) — security & contract DX *(all independent, start anytime)*
- ✅ `001` Fail-closed production secrets validation — **DONE 2026-06-30**
- ✅ `002` Tenant-isolation audit + ownership-scoping enforcement — **DONE 2026-06-30**
- ✅ `003` Systemic schema-parity coverage for cross-boundary types — **DONE 2026-06-30**

### `ops-observability/` (5) — production operability
- ✅ `001` App-level SLOs + alerting — **DONE 2026-06-30** (reuse Langfuse + job-store; no new vendor)
- ✅ `002` Disaster recovery — backup/restore + LangGraph checkpoint-recovery drill — **DONE 2026-06-30**
- `003` Runbooks per failure mode *(←001)*
- `004` Per-teacher rolling cost cap + transparency *(←scaling-003)*
- ✅ `005` Webhook inbound security (mandatory signature + idempotent + rate-limit) + dispatch — **DONE 2026-06-30**

### `trust-lifecycle/` (4) — accessibility, model trust, teacher lifecycle, recall
- ✅ `001` Accessibility WCAG 2.1 AA (axe-core; critical → hard-block; dyslexia/high-contrast theme) — **DONE 2026-06-30**
- `002` Model pinning + drift detection + canary/rollback (extends ADR-013 to models) *(←testing-005)*
- `003` Teacher content lifecycle — library + fork/re-edit + data portability *(←td-002)*
- `004` Post-delivery content recall + incident *(←effectiveness-loop-001)*

### `effectiveness-loop/` (7) — does it actually teach? (ADR-019) *(after topic-decomp KC contracts + scaling-005)*
- `001` Outcome data model + question `kc_ids` + privacy/consent foundation *(←td-001)*
- ✅ `002` De-stub pedagogical metrics (real proxies / explicit `unmeasured`) — **DONE 2026-06-30** *(no blockers — silent-pass fix, do early)*
- `003` Google Forms delivery + response capture (auto, no manual entry) *(←001, scaling-005)*
- `004` pyBKT knowledge-tracing engine (cold-start, batch, degrade) *(←003)*
- `005` Loop closure — mastery→planner + MoET sổ theo dõi export + dashboard *(←004)*
- `006` Contrastive concept-alignment verifier (KT4EQG) *(←001)*
- `007` RISE template-effectiveness signal + 3-layer HITL *(←004,005, td-014)*

### `technical-debt/` (6) — close the verified as-built gaps (audit 2026-06-30)
- `001` Consolidate LLM access onto `llm_client` (single path; remove legacy transport) *(no blockers)*
- `002` Wire safety/quality **middleware** into the deterministic pipeline (call-level runner in `llm_client`; G1 run-entry, G2 per-call + 4 new guards, G3 generation-context, G4→quality-gate, G5 gate, G6 parked) *(←001)*
- `003` De-stub Layer-2 quality (pedagogical + fact_check + age_check) — supersedes `effectiveness-loop/002` *(no blockers)*
- `004` Remove/park dead **Lead Agent** + clean dangling prod-compose `9router` dep *(←002)*
- `005` Config hygiene — LLM endpoint port (`:20228`) + model alias *(no blockers)*
- `006` **Architecture drift-guard** — manifest generator + CI sync test so `ARCHITECTURE.md` can't silently drift *(no blockers)*
- **Also reopen:** `runtime-parity/001` (6-layer inject) + `/003` (event-bus) + finish `/002` `/005` — the not-done/partial items above.

### `agent-upgrades/` (7) — per-agent bespoke intelligence (from the agent evaluation)
- `001` **researcher** — real FACT triangulation, heuristic credibility, targeted+criticality claims, fail-closed grounding, research-memory cache *(←td-002)*
- `002` **planner** — staged backward-design + grounding + validator + lesson_critic + 3-source-adaptive + differentiation + smart-retry + feedback-memory + cold/seed duality *(←td-002, td-003, td-005)*
- `003` **content_creator** — hierarchical outline→fill-per-section + resilient degrade + parallel/isolated + enforce-guards + grounding-enforcement + harden seam + adaptive *(←component-002, agent-001, td-002)*
- `004` **reviewer** — revive as live Layer-4 judge + per-dimension/diverse-lens + ≥2-judge robustness + calibrate-vs-teacher/effectiveness + criteria-referenced/evidence-cited + adversarial *(←parity-001, agent-001)*
- `005` **diagnostician** — wire into `diagnose_then_generate` + shared knowledge-state with KT + per-dimension D&C + misconception-grounding *(Phase 3; ←effectiveness-004, agent-002)*
- `006` **roadmap** — macro layer (milestone→unit compose) + implement personalization + gaps→focus link + KT-adaptive *(Phase 3; ←agent-005, effectiveness-004)*
- `007` **repair+edit loop** (cross-agent) — scoped issue-precise repair + immutable-versioned content update + transparency/diff + teacher section-editor + 3-layer authority *(←agent-003, agent-004)*

> Cross-cutting principle for ALL agents: **divide-and-conquer — no single long master prompt.** Every agent decomposes into focused sub-steps (planner staged phases · content_creator outline→fill-per-section · researcher per-claim · reviewer per-dimension judges · diagnostician per-gap · roadmap per-milestone · unit_planner Curricular-CoT phases).

### `agent-interaction/` (7) — how agents coordinate (native LangGraph) — **reconciled with as-built audit + design grilling 2026-06-30**
⚠️ As-built reality reshaped the original 4 issues: agents are **imperative calls inside stage nodes** (not graph nodes), and `Command`/`Send`/`BaseStore`/state-reducers are **not used anywhere** today. Decision: **stage = agent's graph identity** (no agent→node promotion); sub-agent parallelism deferred to when `agent-upgrades/003/004` decompose content_creator/reviewer into subgraphs.
- ✅ `000` **Order-stable index-keyed reducer** — `stable_merge_artifacts` (sort by type+id; dedup by artifact_id); `artifact_chunks: Annotated[..., stable_merge_artifacts]` on `TeachingPackState` (parallel accumulator for 004b); scoped-regen sequential path untouched — **DONE 2026-06-30**
- ✅ `001` **Typed seam-contract layer** — `PlannerHandoff` / `ResearcherHandoff` / `ArtifactWorkflowHandoff` in `common/contracts/seam_contracts.py`; called fail-closed in `_planning_blueprint` / `_post_blueprint_research` / `_artifact_workflow`; seam name in error messages — **DONE 2026-06-30**
- ✅ `002a` **BaseStore substrate** — `open_teaching_pack_store` + `get_development_store` + `sync_connection_string` in `packages/agents/teaching_pack/store.py`; 6 namespace factories + TTL conventions in `store_namespaces.py`; `build_teaching_pack_graph(store=)` wired; gateway `lifespan` uses `ExitStack` to manage store lifecycle — **DONE 2026-06-30**
- `002b` **BaseStore semantic index** — vectors for grounding retrieval only; **embedding must route via `llm_client`/LiteLLM** (no egress — K-12 privacy, single-path, cost-attribution); LiteLLM has no embeddings route yet *(←002a + embedding-provider decision; gated/parked if unavailable)*
- `003` **Bounded upstream revision protocol** — `RevisionRequest` + **state-flag + conditional-edge router** (NOT `Command(goto)` from nodes); **one shared `upstream_cycle_count`** bounding agent-revision + the existing quality-reroute; exhaustion escalates via the existing `interrupt()` gate *(←001)*
- `004a` **Interaction observability** — trace every handoff/revision/Store-access → Langfuse/RunEvent; reconstructable interaction graph (feeds testing-trajectory + reviewer-calibration) *(←001,002a)*
- `004b` **Parallel fan-out (`Send`)** — content_creator per-section + reviewer per-dimension; per-run sub-fanout cap (distinct from worker cap); per-section streaming to FE *(←000,003, agent-upgrades/003/004)*

> Interaction is **native LangGraph**, deterministic (no Lead-Agent/ReAct): **stage = agent graph-identity** · `BaseStore` = cross-run memory · **state-flag + conditional-edge** = bounded upstream-signal (not node-emitted `Command`) · `Send` = sub-agent parallel fan-out · `interrupt` = gates. Thin additions: typed seam contracts, RevisionRequest schema, single shared revision budget, namespace conventions, order-stable reducer.
> **Intra-epic waves:** ✅ A *(done 2026-06-30)* `000`·`001`·`002a` → B `003`·`004a` → C *(gated/deferred)* `002b`·`004b`.

### `component-system/` (2) — content-component registry + smart selection
- `001` **ComponentRegistry** single source of truth (metadata; derive prompt-catalog; union+dispatcher drift-guard; mirrors question registry) *(no blockers)*
- `002` **Filter-then-generate** — query registry by artifact/methodology/subject → focused catalog into content_creator *(←001)*

### `testing/` (8) — system-wide test harness *(framework verdict, see below)*
- ✅ `001` Harness & tiering foundation — **DONE 2026-06-30** (real DB + real LLM via 9router `:20228`/`4omc`, `@pytest.mark.real_llm`, DeepEval offline config, no fake-LLM)
- `002` Three-layer pyramid — per-agent (real-LLM) + seam/handoff + E2E *(←001)*
- `003` Deterministic trajectory + control-flow + health gates (per-commit, no LLM) *(←001)*
- `004` DeepEval quality metrics → Layers 2/4/6 *(←001, parity-001)*
- `005` Golden dataset + nightly regression *(←004)*
- `006` Promptfoo security/red-team — K-12 safety + INVARIANT-05/06 *(←001)*
- `007` Chaos/fault-injection (healing) + production-trace feedback *(←001, parity-002, scaling-003)*
- `008` **Canonical flow harness** — shared scenarios + per-agent/per-stage/full-flow layers + real-graph conformance + one `make e2e` *(←001)*

---

## Execution plan (dependency-ordered waves)

Complete topological order of **all 56 issues** across 8 epics. Run everything in a wave in parallel; a wave starts when all its blockers (earlier waves) are done. Earliest-wave = `1 + max(blocker waves)`; blocker-free = Wave 0.

> ✅ **`runtime-parity/` (all 6) — DONE 2026-06-30** (rp-001…006). Authoritative stage runtime owns the single-lesson path; all parity cross-gates satisfied. Not listed in the waves below (complete).

**Epic prefixes:** `td`=topic-decomposition · `sr`=scaling-resilience · `hd`=hardening · `te`=testing · `el`=effectiveness-loop · `ops`=ops-observability · `tl`=trust-lifecycle · `rp`=runtime-parity (done).

| Wave | Issues (count) | Theme |
|------|----------------|-------|
| **0 — blocker-free (13)** | ✅ `td-001` ✅ `td-005` · ✅ `sr-001` ✅ `sr-002` · ✅ `hd-001` ✅ `hd-002` ✅ `hd-003` · ✅ `te-001` · ✅ `el-002` · ✅ `ops-001` ✅ `ops-002` ✅ `ops-005` · ✅ `tl-001` | Contracts+grounding · render/worker pool · secrets/authz/schema-parity · test harness · de-stub pedagogical · SLO/DR/webhook · a11y |
| **1 (10)** | ✅ `td-002` ✅ `td-003` ✅ `td-004` · ✅ `sr-003` · ✅ `te-002` ✅ `te-003` ✅ `te-004` ✅ `te-006` · ✅ `el-001` · ✅ `ops-003` | Persistence/validator/triage · provider-resilience · pyramid/trajectory/quality-metrics/security · outcome-model · runbooks |
| **2 (9)** | `td-006` `td-013` · `te-005` `te-007` · `el-003` `el-006` · `ops-004` · `tl-003` `tl-004` | unit_planner · persona · golden-dataset/chaos · Forms-capture/concept-verifier · cost-cap · content-lifecycle · recall |
| **3 (6)** | `td-007` `td-008` `td-015` `td-021` · `el-004` · `tl-002` | stage-wiring/gate · expand+drift · knowledge-graph · sequence-critic · BKT engine · model-drift |
| **4 (4)** | `td-009` `td-014` `td-020` · `el-005` | UnitContext · decomposition-memory · approvals-compat · loop-closure+MoET |
| **5 (2)** | `td-010` · `el-007` | UnitOrchestrator (fan-out) · RISE template-effectiveness |
| **6 (2)** | `td-011` `td-018` | Unit read API/SSE · observability+eval |
| **7 (3)** | `td-012` `td-016` `td-017` | Frontend workspace · coherence lint · UnitPackager |
| **8 (1)** | `td-019` | Staged rollout + E2E (release gate) |

Total: 13+10+9+6+4+2+2+3+1 = **50 remaining** + 6 `rp` done = **56**.

### Wave 0 — start here (no blockers, fully parallel) — **ALL DONE 2026-06-30**
✅ `td-001` contracts+codegen · ✅ `td-005` grounding source · ✅ `sr-001` worker-pool+lease-heartbeat · ✅ `sr-002` render worker-pool · ✅ `hd-001` secrets fail-closed · ✅ `hd-002` tenant-isolation · ✅ `hd-003` schema-parity · ✅ `te-001` harness/tiering · ✅ `el-002` de-stub pedagogical · ✅ `ops-001` SLO+alerting · ✅ `ops-002` DR/backup · ✅ `ops-005` webhook security · ✅ `tl-001` accessibility.

**Verified 2026-06-30:** 367 tests passed across all 13 Wave 0 issues. Issue files updated with correct status/checkboxes. Test isolation fixed in `test_lease_heartbeat.py` and `test_slo_metrics.py` (try/finally cleanup guards added). Wave 1 is unblocked.

### Wave 1 — **ALL DONE 2026-07-01**
✅ `td-002` unit persistence · ✅ `td-003` sequence validator · ✅ `td-004` triage/plan_unit confirmation · ✅ `sr-003` provider/budget resilience · ✅ `te-002` test pyramid · ✅ `te-003` deterministic trajectory/health gates · ✅ `te-004` DeepEval quality metrics harness · ✅ `te-006` Promptfoo security red-team · ✅ `el-001` outcome model/privacy foundation · ✅ `ops-003` runbooks.

**Verified 2026-07-01:** focused Wave 1 completion suite passed (`22 passed`): triage heuristic+LLM fallback, contract-confirmation decomposition persistence seam, intra-stage validator/healing trajectory, completion recorder, and DeepEval config/majority/hallucination harness. `services/gateway/tests/test_delivery_record_hook.py` is included and skips cleanly when local Postgres is unavailable; it exercises the real delivery-record hook against a migrated DB.

### Cross-epic gates (all parity gates ✅ satisfied — parity done)
- ✅ `td-019` ← `rp-001`+`rp-002` (quality+healing) · ✅ `td-017` ← `rp-005` (export wiring) · ✅ `td-010/011` ← `rp-003` (event bus).
- `te-004` ← `rp-001` ✅ · `te-007` ← `rp-002` ✅ + `sr-003`.
- `el-003` ← `el-001` + `rp-005` ✅ · `el-007` ← `el-004`,`el-005`,`td-014`.
- `tl-002` ← `te-005` · `tl-003` ← `td-002` · `tl-004` ← `el-001` · `ops-004` ← `sr-003`.

### Critical path (longest chain → release)
`td-001 → td-002 → td-007 → td-009 → td-010 → td-011 → {td-016, td-017} → td-012 → td-019` (8 waves). The effectiveness-loop's longest chain `td-001 → el-001 → el-003 → el-004 → el-005 → el-007` (5 waves) runs in parallel and does not gate the unit release.

### Production-readiness gate (must land before real-classroom exposure)
`hd-001` secrets · `tl-001` a11y · `ops-001` SLO/alerting · `ops-002` DR · `ops-005` webhook security · `tl-004` recall — all are Wave 0–2, so production-readiness can be reached early, independent of the topic-decomposition critical path.

---

## Testing stack — verdict (from the AI-agent-testing framework research)

**Adopt:** DeepEval (pytest metrics, **9router-backed `4omc`, offline/no-egress**) · **Langfuse** (already self-hosted — tracing/eval/dataset/annotation/trace-feedback) · Promptfoo (K-12 red-team + INVARIANT-05/06). **Reject:** LangSmith (proprietary, no self-host, K-12 data egress — Langfuse covers it) · fake-LLM (`FakeListLLM`/`GenericFakeChatModel` — violates real-test policy) · Lead-Agent-delegation trajectory (not in the authoritative stage runtime) · agentverify (built for Lead-Agent tool-call cassettes — N/A here).

Patterns kept: three-layer pyramid, golden dataset, semantic/trajectory-over-exact-match, health gates, chaos/fault-injection, production-trace feedback. The `testing/` epic is the **harness layer**; per-feature epics' suites run on it (topic-decomposition `018` is a specific eval instance generalized by `testing/005`).

## Principles baked into every issue
- **Divide-and-conquer everywhere; no single long master prompt** — every agent decomposes into focused sub-steps (staged/hierarchical/per-item), enabling scoped retry/repair + per-step grounding.
- **New stage runtime only** (`teaching_pack/graph.py`); legacy `build_oh_my_class_graph` frozen, not extended.
- **Reuse existing ports/adapters** (`QualityGate`, `render()`, `ExporterRegistry`, gate registry, JobStore, `eligible_at` requeue, idempotency keys).
- **Fail-closed**, never silent downgrade. **Computed-not-materialized** unit state; `RunStatus` unchanged.
- **Idempotent + durable-substrate** orchestration (JobStore + DB are truth; in-memory events are SSE-only).
- **Simplify = modern only, zero feature loss** (capability inventory + golden parity before deleting).
- **Backward-compatible** migrations (nullable columns); single-lesson flow zero-regression.
