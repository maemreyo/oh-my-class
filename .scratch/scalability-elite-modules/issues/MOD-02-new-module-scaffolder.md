# [MOD-02] `make new-module KIND=… NAME=…` scaffolder

Status: TODO
Labels: module-standard, tooling, dx
ADR: 033
Depends on: MOD-01

## Context

ADR-033 §Decision.2: a scaffolder `make new-module KIND=… NAME=…` emits a compliant skeleton
(contract + registry entry + test stubs + observability) so modules start compliant by
construction. Today a new module author must hand-assemble a contract, a registry entry, a
guard test, a live test, an observability call, and a manifest/version entry, and gets it
subtly wrong — which is exactly the "each module reinvents retry/enforcement" smell ADR-033
exists to kill.

The `Makefile` already hosts the team's task surface (targets like `gen-schemas`,
`check-schemas`, `test-python`, `check`; help via `## ` comments — see Makefile `help:` at the
tail). There is no `new-module` target today (`grep -n new-module Makefile` is empty). The
per-family shapes the scaffolder must emit already exist as concrete examples:

- **agent**: a `packages/agents/sub_agents/<name>/` package with `nodes.py`, `state.py`,
  `tools.py`, `prompts/`, using `AgentRuntime`/`AgentRuntimeConfig`
  (`packages/agents/sub_agents/content_creator/nodes.py:39-129` is the canonical shape,
  including retry + `runtime.complete_compiled_json_with_retries`), plus an
  `AGENT_CAPABILITIES` entry (`packages/agents/tools/capabilities.py:21-45`).
- **renderer_plugin**: a `packages/renderer/src/plugins/<name>.ts` exporting an
  `ArtifactKindPlugin` with `kind`, `version`, `templateVersion`, `themeVersion`, Zod
  `schema`, `sanitizerPolicy`, `adapt`, `templatePath` (mirror
  `packages/renderer/src/plugins/answer-key.ts:1-59`) + registration in the plugin list
  passed to `createPluginRegistry` (`packages/renderer/src/core/registry.ts:43-47`).
- **middleware**: a `BaseMiddleware` subclass (`packages/agents/middleware/base.py:38-83`)
  with `name`/`order` + an entry in `ORDERED_MIDDLEWARE_LIST`
  (`packages/agents/middleware/registry.py`).
- **exporter**: a `packages/exporters/src/<name>/` module registered in `ExporterRegistry`
  (`packages/exporters/src/index.ts`; consumed by
  `scripts/generate_architecture_manifest.py:74`).
- **quality_layer / gate**: implement the `QualityGate` Protocol
  (`packages/agents/teaching_pack/ports.py:125-130`) / add to the gate registry.

## Scope

- [ ] Add a `new-module` Makefile target: `make new-module KIND=<family> NAME=<snake_or_kebab>`
      with `## Scaffold a compliant module skeleton (KIND=agent|renderer_plugin|middleware|exporter|quality_layer|gate)`.
      Validate `KIND` against the `ModuleFamily` enum defined in MOD-01; fail loudly with a
      usage message on unknown kind or missing NAME.
- [ ] Implement the generator as a Python script `scripts/new_module.py` (invoked by the
      Make target) — not shell templating — so it can import the MOD-01 `ModuleFamily` enum
      and stay in sync. Structure it as pure template functions per family + a thin file-writer.
- [ ] Per family, emit exactly the files needed to satisfy the 6 points by construction:
      - typed contract (Pydantic contract stub in `common/contracts/` for agent/gate;
        Zod schema inline for renderer plugin) and register it in the parity set so
        `make check-schemas` covers it;
      - the registry entry, applied as an explicit edit to the real registry file (append to
        `AGENT_CAPABILITIES` / `ORDERED_MIDDLEWARE_LIST` / plugin list / `ExporterRegistry`) —
        NOT auto-scan;
      - guard test stub + live-path test stub following MOD-01's naming/marker convention,
        with the real-LLM stub pointed at 9Router `:20228` model `4omc` for LLM families;
      - observability wiring: for agents, the `AgentRuntime` construction + module-level
        `emit_run_event(run_id, "step_started"/"step_completed"/"step_failed", …)`
        (`packages/agents/events.py:71-73`); for others, an emit call on entry/exit/failure;
      - fail-closed default in the stub (raise / skip-dependency), never a silent pass;
      - a manifest/version entry stub in the unified index (the one MOD-03 owns).
- [ ] Refuse to overwrite existing files; if a target file exists, abort with a clear message
      listing conflicts (idempotent, safe to re-run only when clean).
- [ ] Print a post-scaffold checklist mapping each generated file to the MOD-01 6-point it
      satisfies, and the next commands to run (`make check-schemas`, `make test-python`,
      MOD-03 drift check).

## Acceptance

- `make new-module KIND=agent NAME=sample_agent` produces a package that (a) imports, (b)
  passes the MOD-01 conformance test, (c) passes MOD-03 drift check, without hand-edits beyond
  the intended TODO business-logic bodies.
- The same holds for `KIND=renderer_plugin`, `KIND=middleware`, `KIND=exporter`,
  `KIND=quality_layer`, `KIND=gate` (one acceptance case per family).
- Registry entries are added by explicit edit to the canonical registry file — verified by a
  test that greps the registry for the new name; no decorator/entry-point auto-discovery.
- Re-running against an existing module aborts without clobbering.
- Generated live-path stubs reference 9Router `:20228` / model `4omc`.
- A test scaffolds each family into a temp dir and asserts MOD-01 conformance passes, so the
  scaffolder can never drift from the standard.

## References

- ADR: `docs/adr/033-specialized-module-standard.md` §Decision.2
- MOD-01 spec (`docs/system/module-standard.md`) — the 6-point mapping and `ModuleFamily` enum
- `Makefile` (`help:`, `gen-schemas`, `check-schemas`, `test-python`, `check`)
- `packages/agents/sub_agents/content_creator/nodes.py:39-129`
- `packages/agents/tools/capabilities.py:21-58`
- `packages/renderer/src/plugins/answer-key.ts:1-59`, `packages/renderer/src/core/registry.ts:43-47`
- `packages/agents/middleware/base.py:38-83`, `packages/agents/middleware/registry.py`
- `packages/exporters/src/index.ts`, `scripts/generate_architecture_manifest.py:74`
- `packages/agents/events.py:71-73`, `packages/agents/runtime.py:34-49`

## Implementation notes

- Production-ready: the scaffolder is the enforcement of "compliant by construction" — its
  own test (scaffold → assert MOD-01 conformance) is the guard that keeps it honest.
- Reuse: import the `ModuleFamily` enum and the per-family registry symbols from MOD-01; do
  not hard-code a second copy of the family list.
- Keep template bodies minimal but real: a working no-op that emits observability and
  fail-closes, with clearly marked `# TODO(business-logic)` seams — not pseudo-code.
- The scaffolder edits registries in place; make those edits deterministic (stable sort /
  append-with-anchor-comment) so diffs are clean and reviewable, honoring "explicit
  registration, no magic".
