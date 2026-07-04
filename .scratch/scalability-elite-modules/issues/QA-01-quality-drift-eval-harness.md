# [QA-01] Quality-drift eval harness

Status: TODO
Labels: quality, ops
ADR: 034
Depends on: none

## Context

Content quality is judged live by the **AdaptiveJudge**, and judge reliability is calibrated
offline against human labels via `scripts/calibrate_judge.py` using **Cohen's kappa**. But there
is no **golden-set regression harness** that periodically re-runs a fixed evaluation set to detect
*content-quality drift* when models, prompts, or the pipeline change. Today a prompt tweak or a
provider/model swap (ADR-034 routing) could silently degrade output quality and only be noticed in
production. At the north-star scale (99.5% run-success, ~5,000 packs/day), a quality regression is
as damaging as an availability regression and must be caught pre-release.

The live judge answers "is this one pack good enough"; this harness answers "did our quality bar
move across a change" — a different, aggregate question requiring a stable golden set and a
calibrated judge.

## Scope

- [ ] **Golden set**: a curated, version-controlled set of representative inputs (across grade
      levels, subjects, artifact types, and both generate + diagnose_then_generate modes) with
      known-good reference expectations / human-labeled quality. Store as fixtures; document
      curation + refresh policy.
- [ ] **Eval runner**: a script/harness that runs the pipeline (or the judged stages) over the
      golden set and scores outputs with the **AdaptiveJudge**, reporting per-dimension and
      aggregate quality scores plus **Cohen's kappa** agreement against the labels (reusing the
      `calibrate_judge.py` kappa machinery).
- [ ] **Drift detection**: compare the current run's aggregate scores + kappa against a stored
      baseline; flag drift when metrics fall outside a configured tolerance (regression in mean
      score, drop in kappa, or a shift in the pass/escalate distribution).
- [ ] **Alert on drift**: emit a drift signal (report + machine-readable result) and, for
      scheduled periodic runs, wire an OPS-04-style warn alert so drift is noticed operationally,
      not just in CI.
- [ ] **Release gate**: run the harness in the pre-release path (coordinate with VER-04
      merge-vs-release contract) so a model/prompt change that regresses the golden set **blocks
      release**. Distinguish the fast CI signal from the fuller pre-release eval if runtime is a
      concern.
- [ ] **Model/prompt provenance**: record which model routing + prompt versions produced each
      eval result so a drift can be attributed to a specific change.

## Acceptance

- Running the harness on the current pipeline produces per-dimension + aggregate quality scores
  and a Cohen's kappa vs the golden labels, plus a written report.
- Injecting a deliberately degraded prompt/model makes the harness detect drift and fail the
  release gate — proven by a test.
- The harness uses the **real AdaptiveJudge** against a **real LLM** (per project testing policy),
  not mocks.
- A scheduled/periodic run emits a drift alert when metrics breach tolerance.
- Each eval result carries model-routing + prompt-version provenance.

## References

- `scripts/calibrate_judge.py` — Cohen's kappa calibration machinery to reuse.
- AdaptiveJudge (live judge) — the scorer the harness drives.
- ADR-029 (quality escalation) — the pass/escalate distribution this watches for shift.
- OPS-04 (alerting) — drift warn alert; VER-04 (merge-vs-release contract) — release-gate wiring.
- ADR-034 decision 11.

## Implementation notes

- The golden set is the asset — invest in coverage (grades/subjects/artifact types/both modes)
  and keep it version-controlled so baselines are meaningful across time.
- Reuse `calibrate_judge.py`'s kappa computation rather than re-deriving it; the harness adds the
  golden-set orchestration + baseline comparison on top.
- Real judge + real LLM per the project's "tests are real, not mock" standard; budget the
  release-gate variant's runtime accordingly (may sample the golden set in fast CI, run full at
  release).
- Keep this distinct from QA-02 (load/perf): QA-01 measures *quality* drift, QA-02 measures
  *throughput/latency* against the SLOs.
