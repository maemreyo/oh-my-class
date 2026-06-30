---
title: De-stub pedagogical metrics (real proxies or explicit unmeasured)
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Fix a silent-pass quality bug independent of KT: `packages/quality/layer2_content/pedagogical.py:61` returns `{metric: True for metric in REQUIRED_METRICS}` — all 7 pedagogical metrics are hardcoded `True`, so the system claims pedagogical quality it never measures (violates fail-closed; runtime-parity 001 wired this layer in, but its pedagogical metrics are fake).

- Audit the 7 `REQUIRED_METRICS`. For each, either **implement a real pre-delivery proxy** (deterministic where possible, real LLM-judge via 9router otherwise) or **mark it `unmeasured`** and exclude it from pass-criteria — **never default to `True`**.
- Real pre-delivery proxies to implement: objective-alignment, Bloom-coverage, cognitive-load (≤4 new KC — reuse `SequenceConsistencyValidator`), readability-level (reuse `readability_checker`), misconception-coverage; concept-alignment is delivered by issue 006.
- Metrics that require post-delivery evidence ("does this actually teach?") are **deferred to the KT effectiveness loop**, not faked at the gate.
- The quality report shows, per metric, `measured`/`unmeasured` transparently; pass-criteria use only measured metrics.

## Acceptance criteria

- [ ] No pedagogical metric defaults to `True`; each is a real proxy or explicitly `unmeasured` (excluded from pass).
- [ ] Implemented proxies (objective-alignment, Bloom-coverage, CLT, readability, misconception-coverage) produce real signals and flag deliberate violations.
- [ ] "Does it teach?" is deferred to the KT loop, not asserted at the pre-delivery gate.
- [ ] The quality report exposes per-metric measured/unmeasured status.
- [ ] Pass-criteria depend only on measured metrics; an all-stub regression cannot recur (a test asserts no hardcoded-True).

## Detailed test suite

(Real LLM via 9router `:20228`/`4omc` for judge proxies; deterministic for the rest.)

- [ ] `packages/quality/tests/test_pedagogical_real.py`: content violating objective-alignment / Bloom-coverage / readability is flagged; compliant content passes.
- [ ] `packages/quality/tests/test_no_stub_metrics.py`: a guard asserts `pedagogical.py` returns no unconditional `True` (anti-silent-pass).
- [ ] same file: an `unmeasured` metric is excluded from pass-criteria and surfaced in the report.
- [ ] Run `uv run pytest packages/quality/tests/test_pedagogical_real.py packages/quality/tests/test_no_stub_metrics.py -v`.

## Blocked by

None - can start immediately
