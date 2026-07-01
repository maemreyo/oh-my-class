---
title: De-stub Layer-2 quality metrics (pedagogical + fact_check + age_check)
status: done
labels: []
created: 2026-06-30
---

## What to build

Three Layer-2 quality modules silently pass (fail-closed violation): `pedagogical.py:61` hardcodes all 7 metrics to `True`; `fact_check.py` returns empty; `age_check.py` returns `True`/`0.0`. Replace with real proxies or explicit `unmeasured` — never default `True`. **Supersedes `effectiveness-loop/002`** (which covered pedagogical only).

- **pedagogical**: implement real pre-delivery proxies (objective-alignment, Bloom-coverage, CLT load, misconception-coverage); concept-alignment comes from `effectiveness-loop/006`. Unimplementable metrics → `unmeasured`, excluded from pass.
- **age_check**: wire to the real `readability_checker` (Flesch-Kincaid) + the age-band table (from grounding) → real age-appropriateness, not `0.0/True`.
- **fact_check**: bounded — extract claims, verify **against the `research_bundle` sources the researcher already gathered** (no external web verification). No sources → `unmeasured`/flag, not fake True.
- Report exposes per-metric `measured`/`unmeasured`; pass-criteria use only measured metrics. These feed the 6-layer gate (`runtime-parity/001`).

## Acceptance criteria

- [x] No Layer-2 metric defaults to `True`; each is a real proxy or explicit `unmeasured`.
- [x] `age_check` uses readability + age-band; `fact_check` verifies against research sources (bounded), flags when ungrounded.
- [x] The quality report shows per-metric measured/unmeasured; a guard test prevents reintroducing hardcoded-True.
- [x] Wired into the 6-layer gate path (consumed by `runtime-parity/001`).

## Detailed test suite

(Real LLM via 9router `:20228`/`4omc`; deterministic where possible.)

- [x] `packages/quality/tests/test_pedagogical_real.py`: content violating objective-alignment/Bloom/readability is flagged; compliant passes.
- [x] `packages/quality/tests/test_fact_check_bounded.py`: a claim unsupported by the research bundle is flagged; a supported one passes; no sources → `unmeasured`.
- [x] `packages/quality/tests/test_age_check_real.py`: age-inappropriate reading level for the grade is flagged.
- [x] `test_no_stub_metrics.py`: asserts no unconditional `True` in pedagogical/fact/age.
- [x] Run `uv run pytest packages/quality/tests/test_pedagogical_real.py packages/quality/tests/test_fact_check_bounded.py packages/quality/tests/test_age_check_real.py -v`.

## Blocked by

None - can start immediately
