---
title: Reviewer — revive as live Layer-4 judge, divide-and-conquer, calibrated
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

The reviewer (G-Eval + majority vote) is well-built but **orphaned** — wired only to the dead lead_agent; the live path uses thin deterministic quality. Revive it and raise review quality (divide-and-conquer; no mega-judge-prompt).

- **Revive as live Layer-4 judge:** wire the reviewer into the authoritative quality path via the `QualityGate` adapter (`runtime-parity/001`), sitting above deterministic Layers 1–3 + (de-stubbed) pedagogical/fact/age.
- **Divide-and-conquer the review:** replace one judge scoring all dimensions with **per-dimension / diverse-lens judges** (format / content / pedagogy / presentation), each focused with its own rubric; prefer diverse lenses over identical judges.
- **Robustness:** guarantee **≥2 judges** (retry failed judges, don't silently drop to 1); compute **inter-rater agreement** → low agreement re-judges/escalates; **rubric anchor examples** (few-shot per score band) to cut variance.
- **No double-judge:** deterministic Layer 1–3 hard-blocks override; the judge does not re-score what they already caught.
- **Calibrated against real signals (raise quality):** track **judge↔teacher-decision agreement (kappa)** + **judge↔effectiveness (KT) correlation** → recalibrate thresholds/rubric ("9/10 means nothing if students didn't learn").
- **Criteria-referenced + evidence-cited:** judge against the lesson_plan objectives + researcher verified-facts (not in a vacuum); each verdict cites the specific span/issue (interpretable → feeds scoped repair). Rubric selected per artifact-type + methodology (`rubric_selector`).
- **Adversarial + escalation:** judges attempt to **refute** (find the worst flaw, default-fail-if-uncertain); strong disagreement escalates to the teacher; panel size/lenses scale by policy (cost-gated).

## Acceptance criteria

- [ ] Reviewer runs in the live quality path as Layer-4 (via parity-001), not only the dead lead_agent path.
- [ ] Review is split into per-dimension/diverse-lens judges (focused rubrics), not one mega-prompt.
- [ ] ≥2 judges guaranteed (retry); inter-rater agreement computed; low agreement escalates; rubric anchors present.
- [ ] Deterministic hard-blocks override; no double-judging of already-caught issues.
- [ ] Judge↔teacher and judge↔effectiveness agreement tracked and used to recalibrate.
- [ ] Verdicts are criteria-referenced (objectives + verified-facts) + evidence-cited; rubric per artifact-type/methodology; adversarial refutation + disagreement-escalation; panel scales by policy.

## Detailed test suite

(Real LLM via 9router `:20228`/`4omc`.)

- [ ] `packages/agents/tests/test_reviewer_live_wiring.py`: a teaching-pack run invokes the reviewer as the Layer-4 judge.
- [ ] `test_reviewer_robustness.py`: 1 failed judge is retried to ensure ≥2; all-fail escalates; low inter-rater agreement escalates.
- [ ] `test_reviewer_criteria_referenced.py`: an artifact missing a stated objective / asserting a non-verified fact is failed with a cited span.
- [ ] `test_reviewer_calibration.py`: judge↔teacher disagreement is recorded and shifts the calibration.
- [ ] Run `uv run pytest -m real_llm packages/agents/tests/test_reviewer_*.py -v`.

## Blocked by

- .scratch/runtime-parity/001-six-layer-quality-gate-adapter.md
- .scratch/agent-upgrades/001-researcher-real-grounding.md
