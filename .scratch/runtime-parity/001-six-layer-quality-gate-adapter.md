---
title: Wire the 6-layer quality system into the teaching-pack runtime
status: done
labels: []
created: 2026-06-30
---

## What to build

Close the hidden quality cliff: the authoritative teaching-pack stage runtime currently runs only the thin `teaching_pack/quality.py` `quality_issues()` (regex placeholder/answer-key + schema + VN-distribution) and **never invokes** the sophisticated `packages/quality` 6-layer system (fact-check, age-appropriateness, PII, readability, pedagogical, HTML validation, **G-Eval 3-judge**, export validation). That rich system is wired only to the FROZEN legacy graph.

The seam already exists: `packages/agents/teaching_pack/ports.py:125` defines `QualityGate` Protocol (`async evaluate(state) -> ArtifactQualityReport`), but `build_teaching_pack_graph` is built with no gate injected and `_render_quality` (`nodes.py:157`) calls `quality_issues()` directly.

- Implement a `SixLayerQualityGate` adapter (in `packages/quality` or a gateway adapter) that satisfies the `QualityGate` Protocol by composing the existing layer modules: layer1 schema, layer2 content (fact_check, age_check, pedagogical, readability, pii, methodology), layer3 html, layer4 G-Eval majority-vote judge, layer6 export readiness.
- Inject it into `build_teaching_pack_graph(...)` (main.py wiring) and have `_render_quality` call the injected `QualityGate.evaluate()`.
- Keep `quality_issues()` as a **fast deterministic pre-check** before the deep gate (fail fast, cheap).
- Preserve hard-blocks (DOCTYPE, external assets, answer-key leakage, native radio, unmanaged JS, brand string) as auto-fail.

LLM-judge layers use the real LLM via 9router (model `4omc`). Gate behind a config flag so it can be rolled out on staging first.

## Acceptance criteria

- [x] A `QualityGate` adapter composes the full 6-layer system behind `ports.py` `QualityGate.evaluate()`.
- [x] `build_teaching_pack_graph` injects the gate; `_render_quality` calls the injected gate (not `quality_issues()` directly), with `quality_issues()` retained as a fast pre-check.
- [x] The teaching-pack path now performs fact-check, age-check, PII, readability, pedagogical, HTML validation, and G-Eval scoring — verified by events/report fields.
- [x] Pass threshold matches the documented bar (`overall ≥ 7.0` AND no critical/hard-block) and routes via `quality_routing` consistently.
- [x] Hard-blocks remain auto-fail.
- [x] Rollout is config-gated; with the gate disabled the prior thin behavior is preserved (no regression in existing teaching-pack tests).

## Detailed test suite

(Real DB + real LLM via 9router port 20228, model `4omc`.)

- [x] `packages/agents/teaching_pack/tests/test_six_layer_gate.py`: an artifact with a factual error / age-inappropriate text / PII is flagged by the injected gate (was silently passing before).
- [x] same file: the injected gate produces an `ArtifactQualityReport` with per-layer scores and a G-Eval judge score.
- [x] `packages/agents/teaching_pack/tests/test_render_quality_wiring.py`: `_render_quality` invokes the injected `QualityGate`, not only `quality_issues()`; the fast pre-check still short-circuits cheap failures.
- [x] Hard-block test: an artifact missing DOCTYPE / with an external asset auto-fails.
- [x] Regression: with the gate flag off, existing teaching-pack quality tests pass unchanged.
- [x] Run `uv run pytest packages/agents/teaching_pack/tests/test_six_layer_gate.py packages/agents/teaching_pack/tests/test_render_quality_wiring.py -v`.

## Blocked by

None - can start immediately
