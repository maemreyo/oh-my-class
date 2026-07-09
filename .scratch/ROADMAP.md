# Architecture & Feature Roadmap — Session 2026-06-30 (updated 2026-07-09)

Index of roadmap ADRs and epics, with the dependency-ordered execution plan and placement notes for newly added priorities. See `docs/system/ARCHITECTURE.md` (as-built) and `docs/system/TESTING.md` (how to test).

> Issue format: each `.scratch/<epic>/NNN-*.md` has **What to build / Acceptance criteria / Detailed test suite / Blocked by**.
> Testing policy (all epics): **real DB + real LLM** via 9router `:20228`, model `4omc` — no mocks/fakes. Deterministic logic tested without LLM; LLM-touching tests tiered per `hardening/003`.
> **2026-07-09 update pass**: corrected Slide Deck track from "zero implemented" to its real per-issue state (many done); added Renderer Rewrite, SD-core, Component Strategist epics that were absent; added AUI, MOD, OPS/QA/SEC/PRIV/VER tracks filed after the last condensing pass; updated LIC/LGH status; verified all via `gh issue list` cross-reference.

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
| `runtime-parity/001` + `technical-debt/003` (Layer-2 quality) | ✅ | ⚠️ **PARTIAL** — gate injected but FED EMPTY DATA: `fact_check` sources always `[]`; 3/5 pedagogical metrics unconditionally pass; no Layer-4 G-Eval / Layer-6 in the gate. |
| `runtime-parity/003` | ✅ | ⚠️ **PARTIAL** — legacy `/run/{id}/status` SSE still reads the old in-memory bus. |
| `runtime-parity/005` | ✅ | ⚠️ **PARTIAL** — `ExporterRegistry.export` returns hardcoded path strings. |
| `technical-debt/002` | ✅ | ⚠️ **PARTIAL** — `stream()` skips `after_call`; MockLLMClient bypasses the runner. |
| `technical-debt/004` | ✅ | ⚠️ **PARTIAL** — Lead Agent gone, but root `docker-compose.prod.yml` still has a dangling `9router` dep. |
| **`topic-decomposition/` (units)** | ✅✅✅ | ❌ **POTEMKIN** — no runtime ever creates a `UNIT_PARENT` row. REAL: `td-001/002/003`. `td-021` sequence_critic & `td-006` unit_planner are deterministic Python, **not** the specced LLM agents. `td-005/008/009/014/015/016/017/018` = zero non-test callers (dark). `td-019` "release-gate E2E" calls `decide()`, never runs end-to-end. `td-004/007/010/011/013` = partially-wired shells whose runtime paths never fire. |
| **`vocabulary-batch/` (12)** | ✅ all | ✅ **REAL (corrected 2026-07-08)** — `_process_cluster` fully chains grounding→synthesis→practice→gate. `LIC-08` found the "no route" theory was **wrong**: the real gap was an unwired `normalize_vocabulary_input`. Now wired into `_artifact_workflow`. Only remaining item: `FEATURE_VOCABULARY_BATCH_V1` defaults `false` (deliberate rollout-flag decision). |
| **`effectiveness-loop/004,005`** | ✅ | ❌ **POTEMKIN** — `el-004` honestly reports local Bayesian EMA model (no more fake pyBKT stamp), but specced pyBKT engine is unbuilt; `el-005` dashboard shows literal `"74%"`; mastery never reaches the planner. `el-003` honestly not-done — so the loop runs on synthetic air. |
| `scaling-resilience/003` | ✅ | ❌ **POTEMKIN** — circuit breaker & error classifier zero callers; `LLMClient.chat` never raises `TransientProviderError`; requeue unreachable. |
| `ops-observability/002` | ✅ | ❌ **POTEMKIN** — DR is row-COUNT only; no `pg_dump`/`pg_restore`. |
| `trust-lifecycle/002` | ✅ | ❌ **POTEMKIN** — `evaluate_model_drift`/`snapshot_models` zero callers; drift never triggers. |
| `testing/004` (DeepEval) | ✅ | ❌ **POTEMKIN** — metrics imported for `__name__` assertions, never `.measure()`'d; not wired into layers 2/4/6. |
| `testing/006` (promptfoo) | ✅ | ❌ **POTEMKIN** — `promptfoo.yaml` never invoked (comment only, no CI step); "security" tests are regex over constant strings. |
| `ops-observability/001,003,005` | ✅ | ⚠️ **PARTIAL** — SLO metrics real but `dispatch_slo_alerts` dead; runbooks exist but not linked from alerts; webhook inbound real but outbound dispatch is TODO. |
| `testing/002` | ✅ | ⚠️ **PARTIAL** — seam tests real; per-agent tests are `pytest.skip` scaffolds. |

---

## ADRs (decisions of record)

| ADR | Title | Scope |
|-----|-------|-------|
| **017** | `docs/adr/017-topic-decomposition-and-unit-fan-out.md` | Two-tier unit fan-out; stateless `UnitOrchestrator`; thin sequence + child expand; smart layers; quality tiers |
| **018** | `docs/adr/018-runtime-parity-and-legacy-decommission.md` | Close hidden capability cliffs in the authoritative stage runtime, then decommission the legacy graph |
| **019** | `docs/adr/019-learning-outcome-effectiveness-loop.md` | Longitudinal subsystem: Google Forms → pyBKT knowledge tracing → mastery feeds planning + RISE template effectiveness |
| **020** | `docs/adr/020-langgraph-send-artifact-fanout.md` | LangGraph-native, wave-based `Send` fan-out for single-run artifact generation |
| **021** | `docs/adr/021-vocabulary-batch-pipeline-mode.md` | Production `vocabulary_batch` mode inside Teaching Pack runtime |
| **022** | `docs/adr/022-semantic-anchor-domain-model.md` | Semantic Anchor / Neo Tu Duy domain model |
| **040–042** | `docs/adr/04{0,1,2}-*.md` | Slide deck as first-class artifact: engine/phases (040), typed layout/block/interaction registry (041), 3 surfaces + quality gates (042) |
| **043–046** | `docs/adr/04{3,4,5,6}-*.md` | Slide deck display preferences (043), real-LLM acceptance harness (044), teaching-session foundation (045), TeachingSession platform (046) |
| **047** | `docs/adr/047-slide-deck-editor-and-ai-assisted-revision.md` | Slide Deck in-browser editor + AI-assisted revision |
| **048** | `docs/adr/048-planner-blueprint-deterministic-by-design.md` | Planner lesson-blueprint generation stays deterministic |
| **049** | `docs/adr/049-slide-deck-remains-deterministic-content-creator-flips.md` | `content_creator`'s 9 non-slide-deck artifact types move section content to real LLM |
| **050** | `docs/adr/050-unit-planner-sequence-critic-deterministic-deferred.md` | `unit_planner`/`sequence_critic` stay deterministic pending `td-006`/`td-021` |

---

## Epics

> **Ground truth is the audit table above.** The ✅ marks below reflect per-issue test status at the time each issue was closed, not necessarily current feature-level reality.

### `runtime-parity/` (6) — **ALL DONE 2026-07-01**, audit-confirmed REAL
`001` 6-layer quality gate *(⚠️ PARTIAL, fed empty data)* · `002` healing→stage recovery · `003` event-bus consolidation *(⚠️ legacy SSE still on old bus)* · `004` decommission legacy 18-node graph · `005` multi-format export *(⚠️ hardcoded path strings)* · `006` collapse sub-agent wrappers.

### `topic-decomposition/` (21) — multi-session unit feature (ADR-017)
> ❌ **AUDIT: POTEMKIN as a feature** — no runtime creates a `UNIT_PARENT` row. Only `td-001/002/003` REAL. Parked pending resurrection (after vocabulary-batch).
- `001`✅ Contracts+Zod codegen · `005`✅ Curriculum grounding source
- `002`✅ Unit persistence+migration · `003` SequenceConsistencyValidator+networkx · `004` Triage stage+`plan_unit` mode
- `013` ClassProfile+persona · `006` `unit_planner` agent *(currently deterministic Python)*
- `021` `sequence_critic` *(deterministic)* · `008` Constrained expand+drift guard · `007` Stage wiring+UNIT_APPROVAL · `014` Decomposition memory
- `009` UnitContext · `015` ClassKnowledgeGraph · `020` Legacy approvals compat
- `010` UnitOrchestrator
- `011` Unit read API+SSE · `016` Coherence lint · `017` UnitPackager · `018` Observability+eval
- `012` Frontend unit workspace
- `019` Staged rollout+E2E *(release gate; audit: calls `decide()`, never runs end-to-end)*

### `scaling-resilience/` (3) — throughput & reliability
`001`✅ Worker pool+lease-heartbeat · `002`✅ Long-lived render worker pool — both DONE 2026-06-30.
- `003` Provider-exhaustion requeue+budget degradation+circuit breaker *(←001; audit: POTEMKIN, zero callers)*

### `hardening/` (3) — **ALL DONE 2026-06-30**, audit-confirmed REAL
`001` Fail-closed secrets validation · `002` Tenant-isolation+ownership-scoping audit · `003` Systemic schema-parity coverage.

### `ops-observability/` (5) — production operability (legacy series)
`001`✅ SLOs+alerting *(⚠️ `dispatch_slo_alerts` dead)* · `002`✅ Disaster recovery *(❌ POTEMKIN, row-count only)* · `005`✅ Webhook inbound security *(⚠️ outbound dispatch TODO)* — all DONE 2026-06-30.
- `003` Runbooks per failure mode · `004` Per-teacher rolling cost cap+transparency *(←scaling-003)*

### `trust-lifecycle/` (4) — accessibility, model trust, teacher lifecycle, recall
`001`✅ Accessibility WCAG 2.1 AA — DONE 2026-06-30, audit-confirmed real.
- `002` Model pinning+drift detection+canary/rollback *(audit: POTEMKIN, zero callers)* · `003` Teacher content lifecycle *(←td-002)* · `004` Post-delivery content recall+incident *(←effectiveness-loop-001)*

### `effectiveness-loop/` (7) — does it actually teach? (ADR-019)
> ❌ **AUDIT: el-004/005 POTEMKIN** — pyBKT unbuilt; dashboard hardcoded; mastery never reaches the planner. `el-003` honestly not-done.
- `001` Outcome data model+`kc_ids`+privacy foundation
- `002`✅ De-stub pedagogical metrics — DONE 2026-06-30
- `003` Google Forms delivery+response capture · `004` pyBKT knowledge-tracing engine · `005` Loop closure — mastery→planner+MoET export+dashboard
- `006` Contrastive concept-alignment verifier (KT4EQG) · `007` RISE template-effectiveness signal+3-layer HITL

### `technical-debt/` (6) — **ALL DONE 2026-07-01** (audit-corrected: 002,003,004 PARTIAL)
`001` Consolidate onto `llm_client` · `002` Wire safety/quality middleware *(⚠️ `stream()` skips `after_call`)* · `003` De-stub Layer-2 quality *(⚠️ PARTIAL)* · `004` Remove Lead Agent *(⚠️ dangling prod-compose dep)* · `005` Config hygiene · `006` Architecture drift-guard.

### `agent-upgrades/` (7) — per-agent bespoke intelligence (none started)
- `001` researcher — FACT triangulation, credibility heuristics
- `002` planner — staged backward-design+grounding+validator+differentiation
- `003` content_creator — hierarchical outline→fill + resilient degrade
- `004` reviewer — revive as live Layer-4 judge, ≥2-judge robustness
- `005` diagnostician — wire into `diagnose_then_generate`
- `006` roadmap agent — macro milestone→unit compose+personalization
- `007` repair+edit loop — scoped issue-precise repair+versioned update

### `agent-interaction/` (7) — how agents coordinate
- `000`✅ Order-stable index-keyed reducer · `001`✅ Typed seam-contract layer *(⚠️ PARTIAL — `ArtifactWorkflowHandoff` fires on legacy path only)* · `002a`✅ `BaseStore` substrate
- `002b` `BaseStore` semantic index *(gated — no embeddings route yet)* · `003` Bounded upstream revision protocol
- `004a` Interaction observability · `004b` Parallel fan-out via Send *(reviewer per-dimension, pending)*

### `artifact-send-fanout/` (8) — **ALL DONE**, audit-confirmed REAL (ADR-020)
`001` state+reducer foundation · `002` `generate_one_artifact` node · `003` wave router+fan-in · `004` scoped-regen parity · `005` concurrency+budget wiring · `006` teacher partial-status UX · `007` rollout+E2E evidence · `008` cleanup legacy imperative path.

### `vocabulary-batch/` (12) — Semantic Anchoring / Neo Tu Duy batch generator (ADR-021, ADR-022)
> ✅ **AUDIT (corrected 2026-07-08): REAL** — internal chain is real and complete; `normalize_vocabulary_input` now wired. Only `FEATURE_VOCABULARY_BATCH_V1` off-by-default remains (deliberate ops decision).
- W0: `001` · W1: `002,003` · W2: `004,006` · W3: `005` · W4: `007,008` · W5: `009,011` · W6: `010` · W7: `012`

### `priority-upgrades/` (5) — **ALL DONE 2026-07-01**, audit-confirmed REAL
`001` Quality flags in approval UI · `002` Per-teacher/class memory · `003` Anki-apkg/flashcard-tsv export · `004` Model tiering per task · `005` Adaptive gate fast-lane.

### `component-system/` (2) — content-component registry+smart selection (not started)
- `001` `ComponentRegistry` single source of truth · `002` Filter-then-generate *(←001)*

### `testing/` (8) — system-wide test harness
`001`✅ Harness&tiering foundation — DONE 2026-06-30, audit-confirmed real.
- `002` Three-layer pyramid *(⚠️ PARTIAL, per-agent tests are skip-scaffolds)* · `003`✅ Deterministic trajectory+control-flow gates
- `004` DeepEval quality metrics→Layers 2/4/6 *(❌ POTEMKIN, never `.measure()`'d)* · `005` Golden dataset+nightly regression *(←004)*
- `006` Promptfoo security/red-team *(❌ POTEMKIN, yaml never invoked)* · `007` Chaos/fault-injection
- `008` **Canonical flow harness** — shared scenarios, real-graph conformance, `make e2e` *(fix for the false-green pattern)*

---

## LLM Integration Completion & Governance track (local issues only — not on GitHub)

> **Status (2026-07-09):** `LIC-01..09` ✅ done. `LIC-10` (`_class_profile` silently discards real `class_info` when `persona_snapshot={}`) 🔵 open. `LGH-01..05,07,08` ✅ done. `LGH-06` (pydantic-settings env-var migration) ⚠️ Phase 1 done, Phases 2-4 pending.

- **`llm-integration-completion/` (LIC-01..10)** — `LIC-01..09` ✅ done. `LIC-10` 🔵 open.
- **`llm-governance-hardening/` (LGH-01..08)** — `LGH-01..05,07,08` ✅ done. `LGH-06` ⚠️ Phase 1/4 done.

**Notable corrections found during implementation:** `LIC-06`'s `concept_alignment` half has no real integration point (left `KNOWN_DARK`); `LIC-07`'s `roadmap_agent` has zero product surface expecting it (left `KNOWN_DARK`); `LIC-08`'s "missing route" premise was wrong — real gap was unwired `normalize_vocabulary_input`.

---

## Slide Deck track (ADRs 040-047; status corrected 2026-07-09 from `gh issue list`)

> **Independent of the `td-*` critical path.**

### SD-core foundation (ADR-040/041/042) — 9 issues — ✅ ALL CLOSED (SD-01..09)
Contracts+schema parity · SlideDeckEngine skeleton+registries · tracer through pipeline · 3-surface rendering with leak-safe projection · registered interactions+media policy · engine quality+healing+scorecard+observability · scoped regeneration from teacher feedback · teacher preview UX inside approval gate · golden fixtures+visual smoke.

### `slide-deck-production-hardening/` (SDH-01..12, ADR-043/044) — 6/12 done

| ID | Status | Title |
|----|--------|-------|
| SDH-01 | ✅ DONE | Display preferences and surface contract |
| SDH-02 | ✅ DONE | Student-safe slide projections and chrome policy |
| SDH-03 | ✅ DONE | Standalone slide deck presentation and print controls |
| SDH-04 | ✅ DONE | App preview Print & sharing panel |
| SDH-05 | 🔵 open | Slide deck print layout and crisp border fidelity |
| SDH-06 | 🔵 open | Adaptive bounded structure and density guards |
| SDH-07 | 🔵 open | Official REAL LLM slide-deck acceptance harness |
| SDH-08 | 🔵 open | Production hardening runbook and release evidence |
| SDH-09 | ✅ DONE | Display preference migration and backward compatibility |
| SDH-10 | 🔵 open | Slide deck observability and evidence lineage |
| SDH-11 | ✅ DONE | Teacher-safe failure UX and recovery messages |
| SDH-12 | 🔵 open | Controls security and sanitizer hardening |

### `slide-deck-teaching-foundation/` (SDTF-01..08, ADR-045) — 6/8 done

| ID | Status | Title |
|----|--------|-------|
| SDTF-01 | ✅ DONE | Session-ready slide IDs and interaction contract |
| SDTF-02 | ✅ DONE | Slide pedagogical roles and planned pacing foundation |
| SDTF-03 | ✅ DONE | Related artifact reference foundation |
| SDTF-04 | ✅ DONE | Student companion view architecture |
| SDTF-05 | 🔵 open | Differentiation and teacher guidance foundation |
| SDTF-06 | ✅ DONE | Annotation overlays and remix lineage |
| SDTF-07 | ✅ DONE | Pedagogical component registry alignment |
| SDTF-08 | 🔵 open | Real-LLM evidence for slide-deck teaching foundation |

### `teaching-session-platform/` (TSP-01..09, ADR-046) — 4/9 done

| ID | Status | Title |
|----|--------|-------|
| TSP-01 | ✅ DONE | Session lifecycle, privacy, and retention policy |
| TSP-02 | ✅ DONE | Anonymous-first join and scoped session role tokens |
| TSP-03 | ✅ DONE | Event log, sync transport, and recovery |
| TSP-04 | 🔵 open | Live teaching cockpit for slide-deck sessions |
| TSP-05 | ✅ DONE | Response collection and analytics governance |
| TSP-06 | 🔵 open | Precomputed branching and teacher-only AI suggestions |
| TSP-07 | 🔵 open | Delivery modes and teacher-confirmed feedback loop |
| TSP-08 | 🔵 open | Real evidence harness for TeachingSession platform behavior |
| TSP-09 | 🔵 open | Teacher-mediated, non-identifiable class recap sharing |

### `slide-deck-editor/` (SDE-01..11, ADR-047) — 3/11 done

| ID | Status | Title |
|----|--------|-------|
| SDE-01 | 🔵 open | Real schema-bound LLM call in ContentMaterializer |
| SDE-02 | ✅ DONE | Full 21-layout/block/interaction registry contract |
| SDE-03 | ✅ DONE | Structured-visual block editor (no freeform WYSIWYG) |
| SDE-04 | ✅ DONE | Dual-path edit API, snapshot versioning, and optimistic locking |
| SDE-05 | 🔵 open | Linear version history with restore |
| SDE-06 | 🔵 open | Versioned exports and re-export-needed indicator |
| SDE-07 | 🔵 open | Editor route, local draft buffer, and explicit-commit save |
| SDE-08 | 🔵 open | AI-assisted, block-scoped rewrite with teacher confirmation |
| SDE-09 | 🔵 open | Extend real-LLM harness with edit/rewrite scenarios |
| SDE-10 | 🔵 open | Independent feature flags and AI-rewrite rate limit |
| SDE-11 | 🔵 open | Lightweight success observability |

### `slide-deck-features/` (SDX-01..06) — 5/6 done

| ID | Status | Title |
|----|--------|-------|
| SDX-01 | ✅ DONE | Bilingual (EN <-> VI) deck translation |
| SDX-02 | ✅ DONE | Teacher-scoped minimal media asset library |
| SDX-03 | ✅ DONE | System-provided deck structure presets |
| SDX-04 | 🔵 open | AI-generated alt-text for AI-authored and teacher-uploaded media |
| SDX-05 | ✅ DONE | PPTX export (no PPTX import) |
| SDX-06 | ✅ DONE | Search/filter on the runs list page |

**Dependency order (unchanged):** `SDH-01/02/06` and `SDTF-01` are entry points. `SDE-01→02→03→04→{05,06}→07→08→{09,10,11}` is the editor's internal chain; `SDE-03` additionally needs `SDTF-01`✅. `SDX-02` needs `SDE-03`✅; `SDX-04` needs `SDE-01`+`SDX-02`✅. `TSP-09` needs `TSP-01`✅+`TSP-05`✅+`TSP-07`.

---

## Renderer Rewrite track (RR-000..016) — ✅ ALL 17 CLOSED

> **Added 2026-07-09 — was absent from previous ROADMAP.** Verified via `gh issue list --state closed`.

`RR-000` golden baselines capture · `RR-001` renderer core kernel with fixture plugin · `RR-002` worker protocol V2 with typed responses · `RR-003` unified theme resolver, sanitizer chokepoint, standalone asset policy · `RR-004` quiz as first Artifact-Kind plugin · `RR-005` worksheet+drill plugins · `RR-006` recap+infographic plugins · `RR-007` lesson+answer_key with audience safety · `RR-008` first-class plugins for missing contract types · `RR-009` teaching_pack bundle plugin · `RR-010` semantic-anchor vocabulary plugins · `RR-011` specialty Artifact UI plugins · `RR-012` i18n catalog, print mode, visual QA smoke · `RR-013` persist rendered HTML + manifest + wire exports · `RR-014` enforce renderer public API boundary + migrate callers · `RR-015` renderer rewrite quality gates in CI · `RR-016` decommission legacy renderer paths.

---

## Component Strategist track (ADR-035..039, CS-01..23)

> **Added 2026-07-09 — mentioned in ADR table but had no epic section.** CS-01..13 all closed; CS-14..23 all open.

### CS-01..13 — ✅ ALL CLOSED
`CS-01` contracts+immutable snapshots · `CS-02` YAML knowledge DB+SQLite index · `CS-03` deterministic selector, scorer, diversity core · `CS-04` provisional/final LangGraph passes behind feature flag · `CS-05` Content Creator fills selected strategy components · `CS-06` strategy quality gates+observability ledger · `CS-07` teacher-facing strategy preview in blueprint approval · `CS-08` golden scenarios, CLI smoke, E2E release gate · `CS-09` explicit fallback graph+feedback conflict semantics · `CS-10` knowledge lifecycle, versioning, capability-manifest governance · `CS-11` cache, privacy, observability-retention boundaries · `CS-12` blueprint objective normalization+strategy lineage · `CS-13` delivery, assessment, budget, slot-fill contracts.

### CS-14..23 — 🔵 ALL OPEN (internal rollout hardening)
`CS-14` hidden/internal rollout controls · `CS-15` minimum strategist telemetry · `CS-16` lock v1 SQLite index to static read-only · `CS-17` internal smoke benchmark · `CS-18` no-match+research-fail degradation explicit · `CS-19` scope+claim guards for non-public MOET mode · `CS-20` Vietnamese/MOET extraction pass for launch cohort · `CS-21` MOET validator+public-compliance QA gate · `CS-22` full public rollout SLO+guarded rollout gate · `CS-23` keep LLM advisor deferred behind explicit future gate.

---

## Artifact UI layer track (AUI-001..017) — 🔵 ALL OPEN

> **Added 2026-07-09 — absent from previous ROADMAP.** 17 open issues on GitHub.

`AUI-001` Port Artifact UI CSS into renderer package · `AUI-002` Family registry and CSS loader · `AUI-003` Eta templates for all artifact UI families + interactivity · `AUI-004` Contract adapters for all families + root-cause session · `AUI-005` Replace `semantic-anchor-projections.ts` with Artifact UI · `AUI-006` Replace `inverse-thinking-renderer.ts` with Artifact UI · `AUI-007` Public API — `renderArtifactUi()` entry point · `AUI-008` Full TDD test suite for Artifact UI · `AUI-009` Visual QA — Playwright screenshots at 375/768/1280 for all families · `AUI-010` Scalability validation — add-a-family checklist and docs · `AUI-011` Wire vocabulary batch exporter to `renderArtifactUi()` · `AUI-012` Wire `agent-renderer.ts` — lesson/answer_key to paper-dossier · `AUI-013` Create transit-route video learning route artifact type · `AUI-014` Port `interactivity.js` + Artifact UI sanitizer layer · `AUI-015` Define `RootCauseSessionData` contract · `AUI-016` CSS loader memoization for batch export performance · `AUI-017` Investigation folder — specify detective/neutral frame as template conditional.

**Internal order:** `AUI-001→002→003→004→{005,006,007}→008→009→010`. `AUI-011..017` largely parallel once `AUI-001..004` land.

---

## Specialized Module Standard track (MOD-01..10) — 🔵 ALL OPEN

> **Added 2026-07-09 — absent from previous ROADMAP.** 10 open issues on GitHub.

`MOD-01` Module Standard spec + 6-point conformance test · `MOD-02` `make new-module KIND=... NAME=...` scaffolder · `MOD-03` Unified module manifest index + drift CI · `MOD-04` Contract-versioning policy + golden-fixture regression · `MOD-05` Per-module fault isolation (timeout + fail-closed boundary + circuit breaker) · `MOD-06` Build Researcher-upgrade module · `MOD-07` Build Accessibility module · `MOD-08` Build Localization module · `MOD-09` Build Differentiation module · `MOD-10` Build Standards-alignment module.

**Order:** `MOD-01→02→03→04→05` (foundation); then `MOD-06..10` in parallel.

---

## Platform / Ops / Quality tracks (added post-2026-07-07, all open on GitHub)

### `OPS-*` (14 open) — infrastructure operability (new series; distinct from legacy `ops-observability/`)
`OPS-01` LLM gateway resilience · `OPS-02` Model routing + per-stage latency budget (p95 pack < 8 min) · `OPS-03` Observability KPI dashboard · `OPS-04` SLO objects + tiered alerting · `OPS-05` Object-storage export writer · `OPS-06` Dedicated worker fleet + queue-depth autoscaling · `OPS-07` Data lifecycle & retention · `OPS-08` Zero-downtime deploys · `OPS-09` Multi-tenancy org/school layer · `OPS-10` Idempotency / exactly-once hardening · `OPS-11` Poison-run dead-letter + replay · `OPS-12` Config & secrets management · `OPS-13` DR / backup-restore runbook *(real-work companion to `ops-observability/002` POTEMKIN verdict — this builds real `pg_dump`/`pg_restore`)* · `OPS-14` Data backfill migrations.

### `VER-*` (5 open) — verification & CI integrity
`VER-01` Live-path-proof CI gate (CodeGraph-powered) + ban tautological tests · `VER-02` Test-taxonomy enforcement + tiered CI cadence · `VER-03` Safety-invariant adversarial + mutation testing · `VER-04` Merge-gate vs release-gate CI contract doc · `VER-05` Observability live-emitter meta-test.

### `QA-*` (3 open) — quality assurance
`QA-01` Quality-drift eval harness · `QA-02` Load / performance test harness · `QA-03` Teacher-dashboard accessibility (WCAG).

### `SEC-*` (1 open) / `PRIV-*` (1 open)
`SEC-01` API rate limiting + abuse limits · `PRIV-01` K-12 data privacy (privacy-by-design).

### Full-Flow Acceptance (FFA-10..14) — ✅ ALL CLOSED
`FFA-10` Headless teacher-scenario driver · `FFA-11` Retire stale legacy /run e2e scripts · `FFA-12` Assessment export coverage (gift/h5p/qti) · `FFA-13` google_forms export scope + dry-run · `FFA-14` Pipeline-mode coverage (diagnose/plan_unit/vocabulary_batch).

---

## Execution plan (dependency-ordered waves) — `td-*` / `priority-upgrades` / `artifact-send-fanout` / `vocabulary-batch` track only

Original topological order of **56 `td`-prefixed-epic issues** across 8 epics, plus `priority-upgrades/` (5) and `artifact-send-fanout/` (8) = **81 tracked issues total** for this track.

> **Wave ✅ marks below are per-issue test status only — several were corrected by the audit table above.** If a wave/epic disagree, the audit table wins.

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

**`artifact-send-fanout/`** placement: `asf-001` W1 → `asf-002` W2 → `asf-003` W3 → `asf-004,005` W4 → `asf-006` W5 → `asf-007` W6 → `asf-008` W7. All done, audit-confirmed real.

**`priority-upgrades/`** placement: `pu-004` W0 → `pu-001,002,003` W1 → `pu-005` W2. All done, audit-confirmed real.

**`vocabulary-batch/`** placement: `vb-001` W0 → `vb-002,003` W1 → `vb-004,006` W2 → `vb-005` W3 → `vb-007,008` W4 → `vb-009,011` W5 → `vb-010` W6 → `vb-012` W7. Per-issue done; corrected 2026-07-08 to REAL (internal chain complete — see audit table).

### Cross-epic gates
`td-019` <- `rp-001`+`rp-002` · `td-017` <- `rp-005` · `td-010/011` <- `rp-003` · `te-004` <- `rp-001` · `te-007` <- `rp-002`+`sr-003` · `el-003` <- `el-001`+`rp-005` · `el-007` <- `el-004,005,td-014` · `tl-002` <- `te-005` · `tl-003` <- `td-002` · `tl-004` <- `el-001` · `ops-004` <- `sr-003`.

### Critical path (longest chain to release)
`td-001 -> td-002 -> td-007 -> td-009 -> td-010 -> td-011 -> {td-016, td-017} -> td-012 -> td-019` (8 waves) — **per-issue complete, but audit shows the feature itself is dark (POTEMKIN)**, so this critical path is not actually cleared for release.

### Production-readiness gate (must land before real-classroom exposure)
`hd-001` secrets · `tl-001` a11y · `ops-001` SLO/alerting · `ops-002` DR *(❌ POTEMKIN — needs real work)* · `ops-005` webhook security · `tl-004` recall.

---

## Testing stack — verdict

**Adopt:** DeepEval (pytest metrics, **9router-backed `4omc`, offline/no-egress**) · **Langfuse** (self-hosted) · Promptfoo (K-12 red-team). **Reject:** LangSmith (proprietary, K-12 data egress) · fake-LLM (violates real-test policy).

Patterns kept: three-layer pyramid, golden dataset, semantic/trajectory-over-exact-match, health gates, chaos/fault-injection, production-trace feedback.

**Real-LLM release gate:** `.github/workflows/real-llm-release-gate.yml` runs `@pytest.mark.real_llm` against live 9router (`:20228`, `4omc`) — currently `workflow_dispatch`-only on a self-hosted runner (9Router runs on personal machine, not containerized). **TODO:** containerize 9Router so this can run on a normal GitHub-hosted runner with a nightly `schedule:` trigger.

---

## Principles baked into every issue
- **Divide-and-conquer everywhere; no single long master prompt** — every agent decomposes into focused sub-steps.
- **New stage runtime only** (`teaching_pack/graph.py`); legacy `build_oh_my_class_graph` frozen, not extended.
- **Reuse existing ports/adapters** (`QualityGate`, `render()`, `ExporterRegistry`, gate registry, JobStore, `eligible_at` requeue, idempotency keys).
- **Fail-closed**, never silent downgrade. **Computed-not-materialized** unit state; `RunStatus` unchanged.
- **Idempotent + durable-substrate** orchestration (JobStore + DB are truth; in-memory events are SSE-only).
- **Simplify = modern only, zero feature loss** (capability inventory + golden parity before deleting).
- **Backward-compatible** migrations (nullable columns); single-lesson flow zero-regression.
