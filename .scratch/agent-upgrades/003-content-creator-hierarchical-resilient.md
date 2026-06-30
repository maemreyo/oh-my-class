---
title: Content_creator — hierarchical divide-and-conquer, resilient, adaptive
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Strengthen the strongest agent: resilience, hierarchical divide-and-conquer (no mega-prompt), hardened seam, grounding-enforcement, adaptive learning.

- **Hierarchical D&C (outline → fill-per-section):** per artifact: (1) outline sections + the teaching-job per section → (2) **fill each section independently** (filtered component catalog from `component-system/002` + per-section grounding) → (3) assemble + coherence pass. Replaces single-shot-per-artifact; enables scoped per-section regen + per-section factual grounding. Bounded section count.
- **Resilience (fix placeholder-fallback that's never invoked):** a section/artifact that fails persistently → emit a placeholder marked `needs_regen` and **continue** (no crash of the whole pack); flag it for scoped-regen/teacher.
- **Parallel + isolated:** generate artifacts/sections concurrently (bounded), failures isolated.
- **Enforce guards in-node:** `validate_no_cdn` + `validate_no_pii` actually gate output (currently exported but not acted on) → repair/fail, aligned with G2 PiiOutputGuard.
- **Grounding-enforcement:** consume the researcher's verified-facts + provenance; **student-facing factual assertions ⊆ verified-set**; `contradicted`/`unverified` facts are caveated/avoided + flagged.
- **Harden planner→content_creator seam:** structured (non-lossy) handoff; **coverage contract HARD** (every objective + Gagné phase surfaces in artifacts); **methodology-alignment validation** (plan says inverse_thinking → artifacts carry its required components).
- **Adaptive:** within-run error-adaptation (a failed-field reminder informs the next section/artifact); cross-run **component-effectiveness memory** (teacher-approved / well-taught component patterns → selection prior).

## Acceptance criteria

- [ ] Artifacts are produced via outline→fill-per-section (bounded), enabling per-section scoped regen and grounding.
- [ ] A persistently-failing section degrades to a `needs_regen` placeholder and does not crash the pack; artifacts/sections generate in parallel, isolated.
- [ ] CDN/PII guards gate output in-node; factual assertions are enforced ⊆ researcher verified-set (contradicted/unverified caveated + flagged).
- [ ] Coverage contract is a hard gate (objectives + Gagné phases covered); methodology required-components are validated present.
- [ ] Within-run adaptation + cross-run component-effectiveness memory influence selection.

## Detailed test suite

(Real LLM via 9router `:20228`/`4omc`.)

- [ ] `packages/agents/tests/test_cc_hierarchical.py`: a multi-section lesson is outlined then filled per-section; one section can be regenerated without touching others.
- [ ] `test_cc_resilience.py`: a forced persistent section failure yields a `needs_regen` placeholder; the pack still completes; other artifacts unaffected.
- [ ] `test_cc_grounding_enforce.py`: an asserted fact not in the verified-set is flagged/caveated; CDN/PII in output is caught in-node.
- [ ] `test_cc_seam_coverage.py`: an artifact missing a plan objective or a methodology's required component fails the coverage/methodology gate.
- [ ] Run `uv run pytest -m real_llm packages/agents/tests/test_cc_*.py -v`.

## Blocked by

- .scratch/component-system/002-filter-then-generate.md
- .scratch/agent-upgrades/001-researcher-real-grounding.md
- .scratch/technical-debt/002-middleware-wiring-and-runner.md
