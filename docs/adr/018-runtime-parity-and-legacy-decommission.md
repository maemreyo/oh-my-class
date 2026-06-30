# ADR-018: Runtime Parity and Legacy Decommission

## Status

**Decided** (2026-06-30) — The authoritative teaching-pack stage runtime must absorb the sophisticated capabilities currently wired only to the FROZEN legacy graph (6-layer quality, 5-strategy healing, multi-format export, consolidated eventing) before the legacy runtime is decommissioned and the sub-agent layer simplified. Companion to ADR-017 (which declared the teaching-pack runtime authoritative).

## Context

A codebase audit (2026-06-30, 7 parallel explore agents + direct verification) found the system mid-migration. The teaching-pack stage runtime (`build_teaching_pack_graph`, run by `TeachingPackExecutor`/`TeachingPackWorker`/`TeachingPackJobStore`) is authoritative, but several documented capabilities exist only as modules wired to the FROZEN legacy graph (`build_oh_my_class_graph`). The result is **silent capability cliffs** — the production path advertises capabilities it does not run.

Verified cliffs:

| Capability | Module exists | Wired into teaching-pack? | Evidence |
|-----------|---------------|---------------------------|----------|
| 6-layer quality (fact-check, age, PII, readability, pedagogical, HTML, G-Eval) | `packages/quality/` | **No** | `_render_quality` calls only `teaching_pack/quality.py::quality_issues()`; `build_teaching_pack_graph` injects no `QualityGate` despite `ports.py` defining the Protocol |
| 5-strategy healing | `healing/orchestrator.py` | **No** | teaching-pack has scoped-regeneration only; `max_healing_attempts` config is dead |
| Multi-format export (gift/h5p/qti/google_forms) | `packages/exporters/src/*` | **No** | `export_finalize` emits only `.html`; exporters never invoked |
| Eventing | `events.py` + `teaching_pack_event_bus.py` | fragmented | two buses; `events.py` also used by `llm/chat.py` |
| Diagnostic / roadmap | sub-agents exist | **No** | no diagnostic/roadmap stage in the 8-stage graph |

Shared (NOT legacy, must be preserved): `Run`/`RunStatus`/`RunEvent` models (used by `teaching_pack_store`/`RunStatusHistory`), the sub-agent node functions, `packages/quality`, `healing/orchestrator.py`, contracts.

## Decision

### 1. Close the cliffs in the authoritative runtime (parity)

- **6-layer quality**: implement a `SixLayerQualityGate` adapter satisfying the existing `teaching_pack/ports.py::QualityGate` Protocol, composing `packages/quality` layers; inject it into `build_teaching_pack_graph`; `_render_quality` calls it (keeping `quality_issues()` as a fast pre-check).
- **Healing**: adapt `HealingOrchestrator` into a recovery hook in `quality_routing`, bounded by `max_healing_attempts`, escalating to the teacher gate on exhaustion.
- **Export**: an `ExporterRegistry` keyed by `ExportFormat`, wired into `export_finalize`; **fail-closed** on a requested format with no exporter (never a silent HTML substitute).
- **Eventing**: consolidate run/stage/SSE on `teaching_pack_event_bus`; correctness never depends on the in-memory `events.py`.

### 2. Decommission the legacy runtime (after parity)

Scoped deletion: remove `build_oh_my_class_graph` + its 18-node wiring, the legacy execution routes (`runs.py` legacy create/run, `routers/approvals.py`), and the `app.state.graph` build. **Keep** shared models and the now-rewired capability modules. Sequence: parity → traffic cutover (frontend already uses `/teaching-packs/*`) → flag off → soak → delete.

### 3. Simplify the sub-agent layer (after decommission) — behavior-preserving

Collapse the 5-file sub-agent pattern to the 3 files the stage runtime uses (`nodes.py`, `state.py`, `prompts/`), deleting the `make_*_agent()` StateGraph wrappers, `*_graph_node`, and `adapters.py` whose only caller was the legacy graph.

**Hard constraint: zero feature loss.** This is a structural modernization only. A per-agent capability inventory must prove every wrapper-provided behavior is still reachable via the node path before deletion; golden parity tests must show identical artifacts/behavior before vs after. Wrappers with a live caller (e.g. `reviewer` if the layer-4 judge uses it) are kept.

### 4. Diagnostic / roadmap

Remain available as modules; ported into the stage runtime only when personalization is needed (ADR-017 topic-decomposition Phase 3), not as legacy-graph nodes.

## Consequences

- The production path regains fact-check, age-appropriateness, PII scrubbing, G-Eval judging, healing, and true multi-format export — critical for K-12 trust.
- Topic-decomposition child runs (ADR-017) inherit real quality/healing/export "for free" once parity lands; its rollout (issue 019) and packager (issue 017) depend on parity 001/002/005.
- One authoritative runtime, one event bus, a leaner sub-agent layer — less confusion, lower maintenance, no capability regression.
- Tracked as the `.scratch/runtime-parity/` epic (001 quality, 002 healing, 003 eventing, 004 decommission, 005 export, 006 simplification).

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Wire capabilities into teaching-pack, then decommission (chosen) | Closes cliffs; one runtime; no feature loss | Sequenced work before cleanup |
| Formally drop the legacy capabilities (ship thin quality) | Least work | Loses fact-check/PII/age/G-Eval — unacceptable for K-12 |
| Keep dual runtimes indefinitely | No migration effort | Permanent confusion; docs misrepresent capability; quality cliff persists |
| Delete legacy first, rebuild capabilities later | Removes dead code fast | Capability gap window in production; risky |
| Simplify sub-agents without parity/inventory | Faster | Risks silent feature loss — explicitly rejected |
