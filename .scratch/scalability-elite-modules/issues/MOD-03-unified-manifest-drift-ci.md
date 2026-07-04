# [MOD-03] Unified module manifest index + drift CI

Status: TODO
Labels: module-standard, ci, tooling
ADR: 033
Depends on: MOD-01

## Context

ADR-033 §Decision.3: keep explicit registration (no auto-scan magic), and extend
`scripts/verify_registry_drift.py` + `architecture.manifest.json` into one index across all
families with a drift CI check — registered ⇒ has contract + tests + reachable; nothing
implemented-but-unregistered.

Today two mechanisms exist but neither enumerates *all* module families:

- `scripts/verify_registry_drift.py` validates content hashes for prompts, templates, themes,
  and rubrics (`build_registry_drift_snapshot` at line 202; `assert_all_registry_hashes_clean`
  at line 211) and methodology-literal drift (`find_methodology_literal_drift` at line 254).
  It does not cover agents, renderer plugins, exporters, middleware, or gates as modules.
- `scripts/generate_architecture_manifest.py` writes `docs/system/architecture.manifest.json`
  (`build_manifest` at line 70) covering stages, routers, run statuses, gate names, gates,
  migrations, export formats, models, wiring. It has no per-module family index.

The registries to enumerate already exist and are the source of truth:
`AGENT_CAPABILITIES` (`packages/agents/tools/capabilities.py:21`), `PluginRegistry.metadata()`
(`packages/renderer/src/core/registry.ts:30-40`), `ExporterRegistry` (used at
`scripts/generate_architecture_manifest.py:74`), `ORDERED_MIDDLEWARE_LIST`
(`packages/agents/middleware/registry.py`), and the teaching-pack gate registry
(`services/gateway/teaching_pack_gate_registry.py`, `TeachingPackGateName`).

The "implemented-but-unregistered" and "registered-but-unimplemented" checks map onto existing
semantics: `bind_agent_tools` already rejects `UNIMPLEMENTED`/`FORBIDDEN`
(`packages/agents/tools/capabilities.py:48-58`), and `PluginRegistry.get` raises on unknown
kind (`packages/renderer/src/core/registry.ts:19-28`).

## Scope

- [ ] Extend the architecture manifest with a `modules` section: one entry per registered
      module across all families, each carrying `{family, name, version, contract, test_paths,
      reachable}` — sourced from the real registries via the MOD-01 `ModuleFamily` mapping. Add
      the `ModulesManifest` TypedDict alongside the existing ones
      (`scripts/generate_architecture_manifest.py:18-68`) and populate it in `build_manifest`.
- [ ] For the renderer family (TS-side), emit plugin metadata via a small Node introspection
      entry that dumps `PluginRegistry.metadata()` to JSON, then fold it into the Python
      manifest builder (mirror how export formats read `ExporterRegistry`). Keep it explicit —
      driven by the shipped plugin list, not a filesystem glob of `plugins/*.ts`.
- [ ] Extend `scripts/verify_registry_drift.py` with a module-index drift check
      `assert_module_index_consistent` that asserts, for every family:
      - **registered ⇒ has contract**: the declared Pydantic/Zod contract resolves and is in
        the `make check-schemas` parity set;
      - **registered ⇒ has tests**: guard + live-path test files exist per MOD-01 naming;
      - **registered ⇒ reachable**: the module is bound/gettable through its family registry
        (agent capabilities bind without raising; plugin `kind` resolves; middleware class is
        in `ORDERED_MIDDLEWARE_LIST`; exporter in `ExporterRegistry`; gate in the gate registry);
      - **nothing implemented-but-unregistered**: discover on-disk module implementations per
        family (e.g. `packages/agents/sub_agents/*/nodes.py`,
        `packages/renderer/src/plugins/*.ts`, `packages/exporters/src/*`) and assert every one
        maps to a registry entry — flag orphans by file:line.
- [ ] Raise `RegistryDriftError` (reuse the existing class at
      `scripts/verify_registry_drift.py:66-69`) with `family:name` issue strings; wire
      `assert_module_index_consistent()` into `main()` (line 283) so `make lint`/CI runs it.
- [ ] Regenerate `docs/system/architecture.manifest.json` (via `write_manifest`) and commit
      the updated file; add a CI check that `build_manifest()` output matches the committed
      file (manifest-drift), consistent with the existing generate+verify split.

## Acceptance

- `docs/system/architecture.manifest.json` gains a `modules` array enumerating every
  registered module in every family with version + contract + tests + reachability.
- `python scripts/verify_registry_drift.py` fails when: a registry entry lacks a contract; a
  registry entry lacks guard/live tests; a module implementation exists on disk with no
  registry entry; or a registered module is not reachable through its family registry.
- The unregistered-implementation scan reports orphans by path (e.g.
  `sub_agent:foo (packages/agents/sub_agents/foo/nodes.py) not in AGENT_CAPABILITIES`).
- CI asserts the committed manifest equals freshly generated output.
- Enumeration is registry-driven; the only filesystem scan is the deliberate
  "implemented-but-unregistered" orphan detector, which is a *negative* check, not discovery.
- MOD-01 conformance test and MOD-03 index read the same `ModuleFamily` mapping (no second
  source of truth).

## References

- ADR: `docs/adr/033-specialized-module-standard.md` §Decision.3
- MOD-01 spec + `ModuleFamily` mapping
- `scripts/verify_registry_drift.py:66-69, 202-244, 254-289`
- `scripts/generate_architecture_manifest.py:18-116, 119-123`
- `packages/agents/tools/capabilities.py:21, 48-58`
- `packages/renderer/src/core/registry.ts:19-40`
- `packages/agents/middleware/registry.py`
- `packages/exporters/src/index.ts`
- `services/gateway/teaching_pack_gate_registry.py`
- Makefile `lint`, `check`, `check-schemas`

## Implementation notes

- Production-ready: this is the single audit surface ADR-033 §Consequences promises ("one
  manifest = one place to audit the whole capability surface"). Make the `modules` section
  complete, not a subset.
- Big-bang: land all five families at once; a half-covered index gives false confidence.
- Reuse `RegistryDriftError` and the existing generate/verify pattern; do not invent a parallel
  error type or CI mechanism.
- The TS→JSON introspection step must be deterministic and offline (no dev server); dump from
  the shipped registry module, sorted by kind.
- Keep the orphan scan's allow-list explicit (mirror `METHODOLOGY_DRIFT_ALLOWED_PARTS` at
  `scripts/verify_registry_drift.py:35-63`) for legitimately-unregistered helpers.
