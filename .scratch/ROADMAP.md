# Architecture & Feature Roadmap — Session 2026-06-30

Index of everything produced this session: 2 ADRs + 4 epics (34 issues), with the dependency-ordered execution plan.

> Issue format: each `.scratch/<epic>/NNN-*.md` has **What to build / Acceptance criteria / Detailed test suite / Blocked by**.
> Testing policy (all epics): **real DB + real LLM** via 9router `:20228`, model `4omc` — no mocks/fakes. Deterministic logic tested without LLM; LLM-touching tests tiered per `hardening/003`.

---

## ADRs (decisions of record)

| ADR | Title | Scope |
|-----|-------|-------|
| **017** | `docs/adr/017-topic-decomposition-and-unit-fan-out.md` | Two-tier unit fan-out (parent `plan_unit` run → independent child `generate_pack` runs); stateless `UnitOrchestrator`; thin sequence + child expand; smart layers; quality tiers |
| **018** | `docs/adr/018-runtime-parity-and-legacy-decommission.md` | Close hidden capability cliffs in the authoritative stage runtime, then decommission the legacy graph and simplify sub-agents (behavior-preserving) |

---

## Epics

### `runtime-parity/` (6) — close capability cliffs, then decommission *(prerequisite)*
The authoritative teaching-pack runtime runs thin quality/export and no healing; the rich modules are wired only to the FROZEN legacy graph. Close via existing ports, then remove legacy.
- `001` Wire 6-layer quality via `QualityGate` port
- `002` Wire healing orchestrator → stage recovery *(←001)*
- `003` Consolidate the two event buses onto `teaching_pack_event_bus`
- `005` Wire multi-format exporters (`ExporterRegistry`) into `export_finalize`
- `004` Decommission legacy 18-node graph *(←001,002,003)* — scoped delete; keep shared `Run`/`RunStatus` + modules
- `006` Collapse dead sub-agent StateGraph wrappers, **zero feature loss** *(←004)*

### `topic-decomposition/` (21) — multi-session unit feature (ADR-017)
- `001` Contracts + Zod codegen · `005` Curriculum grounding source *(no blockers)*
- `002` Unit persistence + migration *(←001)* · `003` SequenceConsistencyValidator + networkx *(←001)* · `004` Triage stage + `plan_unit` mode *(←001)*
- `013` ClassProfile + persona *(←001,002)* · `006` `unit_planner` agent *(←001,003,005)*
- `021` `sequence_critic` *(←006)* · `008` Constrained expand + drift guard *(←001,006)* · `007` Stage wiring + UNIT_APPROVAL *(←002,006)* · `014` Decomposition memory *(←006,007)*
- `009` UnitContext (theme/research/persona) *(←007,008,013)* · `015` ClassKnowledgeGraph *(←003,006,013)* · `020` Legacy approvals compat *(←007)*
- `010` UnitOrchestrator *(←002,007,009)*
- `011` Unit read API + SSE *(←001,010)* · `016` Coherence lint *(←010,011)* · `017` UnitPackager *(←010,011,parity-005)* · `018` Observability + eval *(←006,010)*
- `012` Frontend unit workspace *(←011)*
- `019` Staged rollout + E2E *(←012,016,017,018,parity-001,parity-002)* — **release gate**

### `scaling-resilience/` (3) — throughput & reliability
- `001` Worker pool + intra-worker concurrency + **lease-heartbeat** (fixes latent double-execution)
- `002` Long-lived render worker pool + version pin + concurrency cap
- `003` Provider-exhaustion requeue + budget degradation + circuit breaker *(←001)*

### `hardening/` (4) — security & DX *(all independent, start anytime)*
- `001` Fail-closed production secrets validation
- `002` Tenant-isolation audit + ownership-scoping enforcement
- `003` Test tiering (fast deterministic vs real-LLM eval)
- `004` Systemic schema-parity coverage for cross-boundary types

---

## Execution plan (dependency-ordered waves)

Run everything in a wave in parallel; a wave starts when its blockers (earlier waves) are done.

| Wave | Issues | Theme |
|------|--------|-------|
| **0** | parity `001` `003` `005` · scaling `001` `002` · hardening `001` `002` `003` `004` · td `001` `005` | Close cliffs + hardening + contracts/grounding — all blocker-free |
| **1** | parity `002` · scaling `003` · td `002` `003` `004` | Healing; resilience; persistence/validator/triage |
| **2** | parity `004` · td `006` `013` | Decommission legacy; unit_planner; persona |
| **3** | parity `006` · td `007` `008` `021` `014` | Simplify; stage-wiring/gate; expand; critic; memory |
| **4** | td `009` `015` `020` | UnitContext; knowledge graph; approvals compat |
| **5** | td `010` | UnitOrchestrator (fan-out) |
| **6** | td `011` `016` `017` `018` | Read API/SSE; coherence; packager; observability |
| **7** | td `012` | Frontend unit workspace |
| **8** | td `019` | Staged rollout + E2E (release gate) |

### Cross-epic gates (must respect)
- **td `019`** (unit rollout) is blocked by **parity `001`+`002`** → units never ship on thin quality / no healing.
- **td `017`** (UnitPackager) is blocked by **parity `005`** → per-session multi-format export must work at single-run level first.
- **td `010/011`** use `teaching_pack_event_bus` (parity `003`), correctness via `TeachingPackJobStore` + DB.

### Critical path
`td 001 → 002 → 007 → 009 → 010 → 011 → {016,017,018} → 012 → 019` (with parity `001/002/005` landing before `019`/`017`).

---

## Principles baked into every issue
- **New stage runtime only** (`teaching_pack/graph.py`); legacy `build_oh_my_class_graph` frozen, not extended.
- **Reuse existing ports/adapters** (`QualityGate`, `render()`, `ExporterRegistry`, gate registry, JobStore, `eligible_at` requeue, idempotency keys).
- **Fail-closed**, never silent downgrade. **Computed-not-materialized** unit state; `RunStatus` unchanged.
- **Idempotent + durable-substrate** orchestration (JobStore + DB are truth; in-memory events are SSE-only).
- **Simplify = modern only, zero feature loss** (capability inventory + golden parity before deleting).
- **Backward-compatible** migrations (nullable columns); single-lesson flow zero-regression.
