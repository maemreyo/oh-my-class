# [MOD-04] Contract-versioning policy + golden-fixture regression

Status: TODO
Labels: module-standard, contracts, testing
ADR: 033
Depends on: MOD-01

## Context

ADR-033 §Decision.4: additive changes are non-breaking; breaking changes bump
`schema_version` + add a boundary adapter + golden-fixture regression; stored snapshots
re-render only via their pinned `renderer_version`.

The versioning fields already exist. `ArtifactContent` in `common/contracts/artifact.py`
carries `artifact_type` (Literal, line 53), `theme`, `title`, `sections`, `metadata`,
`accessibility` (lines 57-68). Renderer plugins carry `version`, `templateVersion`,
`themeVersion`, and a `sanitizerPolicy.version` (`packages/renderer/src/plugins/answer-key.ts:48-59`;
`PluginRegistry.metadata()` at `packages/renderer/src/core/registry.ts:30-40`). The
grounding confirms `renderer_version`, `template_version`, `theme_version`, `schema_version`
exist and snapshots pin renderer version. Pydantic↔Zod parity is enforced by
`scripts/generate_zod_schemas.py` (`make gen-schemas` / `make check-schemas`).

What is missing: a written policy for what "additive-safe vs breaking" means per family, an
enforcement that a breaking change is accompanied by a `schema_version` bump + boundary
adapter, and a golden-fixture corpus that proves old artifacts still validate and render under
the versions they were created with.

## Scope

- [ ] Write `docs/system/contract-versioning.md`: define additive-safe (new optional field,
      new enum member only if consumers already default-tolerant, widening a bound) vs.
      breaking (removing/renaming a field, tightening a bound, changing a Literal in a way that
      rejects prior values, changing `sections` semantics). Specify the required response to a
      breaking change: bump `schema_version`, add a boundary adapter old→new, add a golden
      fixture at the old version. Reference ADR-033 §Decision.4.
- [ ] Establish a golden-fixture corpus `tests/golden/artifacts/<artifact_type>/<schema_version>/`
      with, per artifact type and schema version: an input JSON artifact + a pinned
      `renderer_version` + the expected rendered standalone-HTML snapshot (or its content hash,
      consistent with the hash approach in
      `scripts/verify_registry_drift.py:107-108, 218-234`).
- [ ] Add a regression test `tests/test_contract_versioning_golden.py` that, for every golden
      fixture: (a) validates the input against the Pydantic contract for its declared
      `schema_version`; (b) renders it through the *pinned* `renderer_version`; (c) asserts the
      output equals the stored snapshot/hash. A fixture that no longer validates or renders is
      a hard failure.
- [ ] Add a boundary-adapter seam: a registry mapping `(artifact_type, from_schema_version) ->
      adapter` that upgrades an old artifact to the current schema. The golden test asserts
      that every historical `schema_version` present in the corpus has either an identity path
      (still valid) or a registered adapter to current.
- [ ] Add a CI guard that fails a PR which changes a contract field in a breaking way without
      (a) a `schema_version` bump and (b) a new golden fixture at the prior version. Implement
      by diffing the contract's field set/bounds against the committed golden fixtures'
      declared versions; integrate with `make check`.
- [ ] Ensure the renderer honors pinned versions on re-render: when a snapshot declares
      `renderer_version` / `template_version` / `theme_version`, the golden test drives the
      renderer at those versions (via `PluginRegistry` metadata), not "latest".

## Acceptance

- `docs/system/contract-versioning.md` exists with the additive-vs-breaking taxonomy and the
  required-response checklist.
- `tests/golden/artifacts/**` contains at least one fixture per current artifact type +
  schema version, each with a pinned renderer version and expected output.
- `tests/test_contract_versioning_golden.py` validates + renders every fixture and matches the
  stored snapshot; removing a field from a contract without a fixture/adapter/version bump
  fails CI.
- Every historical `schema_version` in the corpus resolves to current via identity or a
  registered boundary adapter.
- Re-render uses the fixture's pinned `renderer_version`, proving snapshot reproducibility.
- Additive changes (adding an optional field) pass without a version bump; a negative test
  confirms a breaking change is blocked.

## References

- ADR: `docs/adr/033-specialized-module-standard.md` §Decision.4
- MOD-01 spec (6-point standard, point 1 typed contract, point 6 version entry)
- `common/contracts/artifact.py:46-110`
- `packages/renderer/src/plugins/answer-key.ts:48-59`, `packages/renderer/src/core/registry.ts:30-40`
- `scripts/generate_zod_schemas.py`, Makefile `gen-schemas` / `check-schemas` / `check`
- `scripts/verify_registry_drift.py:107-108, 218-234` (content-hash snapshot pattern)

## Implementation notes

- Production-ready: this is the safety net that lets modules evolve without silently breaking
  stored teacher artifacts — the corpus must include real, representative artifacts, not toy stubs.
- Reuse the existing content-hash discipline from `verify_registry_drift.py` for snapshot
  comparison rather than a new fuzzy-diff mechanism.
- The boundary-adapter registry is a plain explicit dict (no auto-discovery), consistent with
  ADR-033 §Decision.3.
- Coordinate naming with MOD-01: golden test files must satisfy the guard/live-path naming so
  MOD-03's "registered ⇒ has tests" check counts them.
- Keep the breaking-change CI guard conservative (false-negatives worse than false-positives):
  when in doubt, require the bump.
