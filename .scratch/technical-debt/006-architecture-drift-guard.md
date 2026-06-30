---
title: Architecture doc anti-drift guard (keep ARCHITECTURE.md synced with code)
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Keep `docs/system/ARCHITECTURE.md` honest automatically, so it can't silently drift from the code (the exact failure that made the previous doc wrong). Two complementary mechanisms:

1. **Generate the volatile facts** instead of hand-writing them: a script emits a machine-readable manifest (`docs/system/architecture.manifest.json`) from code — stage list (`TeachingPackStage`), router list + prefixes, `RunStatus` values, gate names (`teaching_pack_gate_registry`), Alembic migration count, exporter-registry supported/unsupported formats, codegen `MODELS` registry, and **wiring booleans** (`quality_gate_injected`, `middleware_runner_active`, `lead_agent_present`). The doc references these (or they are inlined by the generator).

2. **Drift test in CI** (`tests/test_architecture_sync.py`): assert the manifest's claims match reality — e.g. the stages in code == documented stages; `build_teaching_pack_graph` is/ isn't called with a `quality_gate`; exporter registry's functional formats == documented; no `OhMyClassState` live consumer if doc says removed. Fail the build when code and doc disagree.

Scope to **structural, machine-checkable** claims (lists + wiring booleans) — prose/intent stays human-authored. Run on every PR.

## Acceptance criteria

- [ ] A generator emits `architecture.manifest.json` from code (stages, routers, RunStatus, gates, migrations, export formats, codegen models, wiring booleans).
- [ ] `tests/test_architecture_sync.py` fails when a manifest claim diverges from code (proven by a deliberate injected divergence).
- [ ] The wiring booleans include `quality_gate_injected`, `middleware_runner_active`, `lead_agent_present`, `legacy_graph_present`.
- [ ] CI runs the drift test on every PR; the doc cites/embeds the manifest for volatile lists.
- [ ] A short "how this doc stays in sync" note is added to `ARCHITECTURE.md`.

## Detailed test suite

- [ ] `tests/test_architecture_sync.py`: manifest matches code; flipping a wiring boolean (e.g. injecting/removing quality_gate) makes the test fail until the manifest regenerates.
- [ ] Generator test: running the generator twice is stable (deterministic) and reflects a stage added to the enum.
- [ ] Run `uv run pytest tests/test_architecture_sync.py -v` and the generator in CI.

## Blocked by

None - can start immediately
