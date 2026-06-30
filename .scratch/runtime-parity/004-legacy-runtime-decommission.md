---
title: Decommission the legacy 18-node graph runtime
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Once the teaching-pack runtime reaches capability parity (parity issues 001–003), remove the FROZEN legacy graph runtime to end the dual-runtime confusion (ADR-017 declares it legacy). This is a **scoped deletion** — only legacy-only code is removed; shared models and capability modules are kept (they are rewired by the parity issues).

**Delete (legacy-only):**
- `build_oh_my_class_graph` + the 18-node wiring in `packages/agents/graph.py`.
- Legacy execution routes that invoke `app.state.graph`: `runs.py` legacy create/run path and `routers/approvals.py`.
- `app.state.graph` build in `main.py`.
- Legacy-only tests (18-node flow / blueprint-gate-via-legacy).

**Keep (shared — do NOT delete):**
- `Run`, `RunStatus`, `RunEvent` models (used by `teaching_pack_store` / `RunStatusHistory`).
- Sub-agents (`planner`, `researcher`, `content_creator`, `reviewer`, `diagnostician`, `roadmap_agent`).
- `packages/quality` (6-layer) and `healing/orchestrator.py` — rewired by parity 001/002.

**Sequence:** parity (001–003) → confirm zero live traffic on legacy execution routes (frontend creates only via `/teaching-packs/*`; legacy `/run` create + `/run/approve` unused) → flag `app.state.graph` build off by default → soak → delete legacy-only code.

Diagnostic/roadmap are ported into the stage runtime only when personalization is needed (topic-decomposition Phase 3); until then they remain available as modules, not as legacy-graph nodes.

## Acceptance criteria

- [ ] No code path builds or invokes `build_oh_my_class_graph` / `app.state.graph`.
- [ ] Legacy execution routes (`runs.py` legacy create/run, `approvals.py`) are removed or return a clear 410/deprecation; the frontend uses only `/teaching-packs/*`.
- [ ] Shared models (`Run`/`RunStatus`) and capability modules (`packages/quality`, `healing`, sub-agents) remain intact and used by the teaching-pack runtime.
- [ ] `import-linter` boundaries still pass; no dangling imports of removed legacy symbols.
- [ ] AGENTS.md / ARCHITECTURE.md updated to a single authoritative runtime.

## Detailed test suite

(Real gateway app + real DB; full suite.)

- [ ] `services/gateway/tests/test_no_legacy_runtime.py`: `app.state.graph` is absent/disabled; legacy create/approve routes are gone or 410.
- [ ] Grep/boundary test: no live import of `build_oh_my_class_graph` outside deleted/tests; `import-linter` passes.
- [ ] Shared-survival test: a teaching-pack run still uses `Run`/`RunStatus` and the 6-layer/healing modules (parity intact).
- [ ] Regression: `make test` and `make check` pass; frontend e2e unaffected.
- [ ] Run `make check` and `uv run pytest services/gateway/tests/test_no_legacy_runtime.py -v`.

## Blocked by

- .scratch/runtime-parity/001-six-layer-quality-gate-adapter.md
- .scratch/runtime-parity/002-healing-orchestrator-stage-recovery.md
- .scratch/runtime-parity/003-event-bus-consolidation.md
