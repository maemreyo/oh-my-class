# [MOD-01] Specialized Module Standard spec + 6-point conformance test

Status: TODO
Labels: module-standard, docs, testing
ADR: 033
Depends on: none

## Context

ADR-033 (`docs/adr/033-specialized-module-standard.md`) decides that every specialized
capability — LLM sub-agent, renderer plugin, exporter, quality layer, middleware, gate —
conforms to one cross-cutting 6-point standard rather than a shared God-base-class. Today
each family has its own registry and its own conventions, but the standard is only prose in
the ADR. There is no single authoritative document a module author can read, and nothing
mechanically enforces the 6 points, so "compliant" is an opinion, not a fact.

The families and the patterns to reuse already exist:

- Renderer plugin registry: `packages/renderer/src/core/registry.ts` (`PluginRegistry`,
  `createPluginRegistry`) with plugins in `packages/renderer/src/plugins/*.ts` and the
  plugin contract in `packages/renderer/src/core/types.ts` (`ArtifactKindPlugin`,
  `PluginMetadata`). Plugins already carry `version`, `templateVersion`, `themeVersion`,
  `sanitizerPolicy.version` (see `packages/renderer/src/plugins/answer-key.ts:48-59`).
- Agent capabilities: `AGENT_CAPABILITIES` and `bind_agent_tools` in
  `packages/agents/tools/capabilities.py:21-58` — `bind_agent_tools` already raises
  `ToolUnavailableError` for `UNIMPLEMENTED`/`FORBIDDEN`, i.e. "no stub bound".
- Middleware: `BaseMiddleware` ABC in `packages/agents/middleware/base.py:38-83`, explicitly
  registered in `packages/agents/middleware/registry.py` via `ORDERED_MIDDLEWARE_LIST`.
- Quality gate boundary: `QualityGate` Protocol in
  `packages/agents/teaching_pack/ports.py:125-130`.
- Exporters: `packages/exporters/src/*` with `ExporterRegistry` used by the manifest builder
  (`scripts/generate_architecture_manifest.py:74-107`).
- Runtime: `AgentRuntime` / `AgentRuntimeConfig` in `packages/agents/runtime.py:34-49`.
- Observability: `ObservabilityEvent` + `emit_run_event`/`publish_event` in
  `packages/agents/events.py:44-82`; the event-type Literal already includes
  `step_started`/`step_completed`/`step_failed` and `breaker_tripped`
  (`packages/agents/events.py:23-41`).
- Versioning fields already exist: `renderer_version`, `template_version`, `theme_version`,
  `schema_version`; snapshots pin renderer version.

The 6-point Module Standard (ADR-033 §Decision.1):
(1) typed I/O contract (Pydantic↔Zod parity); (2) capability declaration in its family
registry (no stub/unimplemented bound); (3) guard + live-path behavioral tests;
(4) `ObservabilityEvent` on entry/exit/failure; (5) fail-closed default;
(6) manifest/version entry.

## Scope

- [ ] Write `docs/system/module-standard.md`: the authoritative spec. For each of the 6
      points, give (a) the requirement, (b) the concrete per-family expression (how a
      renderer plugin vs. an agent vs. a middleware vs. an exporter vs. a gate satisfies it),
      (c) the exact symbol/registry/file the point maps to, (d) how the conformance test
      checks it. Link back to ADR-033.
- [ ] Define a single `ModuleFamily` enum/list (`agent`, `renderer_plugin`, `exporter`,
      `middleware`, `quality_layer`, `gate`) and, per family, the introspection source of
      truth already used elsewhere (e.g. `AGENT_CAPABILITIES`, `PluginRegistry.metadata()`,
      `ExporterRegistry`, `ORDERED_MIDDLEWARE_LIST`). This enum is the seam MOD-02/03 build on.
- [ ] Add a machine-checkable conformance test `tests/test_module_standard_conformance.py`
      (pytest) that, for every registered module in every family, asserts all 6 points:
      1. **Typed contract**: module names a Pydantic contract that exists and imports; where a
         Zod counterpart is expected, `make check-schemas`
         (`scripts/generate_zod_schemas.py`) covers it — assert the type is included in the
         parity set, not re-implement parity here.
      2. **Capability declaration / no stub bound**: for agents, every declared capability is
         `IMPLEMENTED` or explicitly `FORBIDDEN`/`UNIMPLEMENTED` (never bound); for renderer
         plugins, the `kind` is present in the shipped registry; assert nothing is bound that
         `bind_agent_tools` would reject.
      3. **Guard + live-path tests exist**: assert a test file exists per module matching the
         naming convention the spec defines (e.g. `test_<module>_guard` and
         `test_<module>_live` markers), and that the guard test is collectible.
      4. **Observability**: assert the module's entry/exit/failure path emits
         `ObservabilityEvent` (for agents: uses `AgentRuntime` whose `_call_once` logs, plus a
         module-level `step_started`/`step_completed`/`step_failed`); for others, assert an
         emit call is reachable. Enforce via a static/import check where a runtime check is
         not feasible.
      5. **Fail-closed default**: assert the module has a declared default behavior on
         error/unavailability that is closed (raise / skip-dependency / gate-block), never
         silent-pass. Cross-check the agent-wrapper skip policy (fail-closed, not silent
         degradation).
      6. **Manifest/version entry**: assert the module appears in the unified manifest index
         (the index MOD-03 extends) with a version field.
- [ ] Provide a small in-repo "reference module" fixture per family (or point at an existing
      compliant module, e.g. `answer-key.ts` for renderer, `researcher` for agent) that the
      conformance test uses as a positive control, plus a deliberately non-compliant fixture
      as a negative control (test asserts it is flagged).
- [ ] Wire the conformance test into `make test-python` / `make check` so CI runs it.

## Acceptance

- `docs/system/module-standard.md` exists and documents all 6 points with per-family
  expression and file:line references to the reused patterns.
- `tests/test_module_standard_conformance.py` runs green against the current registered
  module set and fails when the negative-control fixture is introduced.
- The test enumerates modules from the real registries (`AGENT_CAPABILITIES`,
  `PluginRegistry`, `ExporterRegistry`, `ORDERED_MIDDLEWARE_LIST`, gate registry) — no
  hard-coded module list that can silently drift.
- No auto-scan/decorator magic introduced; enumeration is via explicit registries only
  (ADR-033 §Decision.3, alternatives table row 3).
- `make check` invokes the conformance test.

## References

- ADR: `docs/adr/033-specialized-module-standard.md`
- `packages/agents/tools/capabilities.py:21-58`
- `packages/agents/middleware/base.py:38-83`, `packages/agents/middleware/registry.py`
- `packages/agents/teaching_pack/ports.py:125-130`
- `packages/renderer/src/core/registry.ts:4-47`, `packages/renderer/src/core/types.ts`
- `packages/renderer/src/plugins/answer-key.ts:48-59`
- `packages/agents/events.py:23-82`
- `packages/agents/runtime.py:34-49`, `152-210`
- `scripts/generate_architecture_manifest.py:70-116`
- `scripts/generate_zod_schemas.py`, Makefile targets `check-schemas`, `gen-schemas`

## Implementation notes

- Production-ready, not a patch: the spec is the contract MOD-02..05 and MOD-06..10 all cite.
  Get the 6-point mapping precise per family before writing the test.
- Big-bang + guard tests: land the spec and the conformance test together; the test is itself
  the guard for the whole standard.
- Reuse, don't reinvent: the conformance test is a thin assertion layer over the existing
  registries and `make check-schemas`; it must not duplicate parity logic or maintain its own
  module list.
- Point (3)'s "live-path" test does not have to run a live LLM in the conformance test itself
  — it asserts the *existence and markers* of guard+live tests. The live tests themselves run
  under the real-LLM suite (9Router `:20228`, model `4omc`) per the testing standard.
- Keep the spec's per-family table the single place that maps family → registry symbol →
  version field; MOD-03's drift CI reads the same table.
