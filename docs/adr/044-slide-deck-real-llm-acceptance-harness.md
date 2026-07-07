# ADR-044: Slide Deck Real-LLM Acceptance Harness

## Status

**Proposed** (2026-07-07) — Defines real-LLM acceptance evidence for production-ready slide-deck hardening. Deterministic tests remain useful technical guards, but they are not sufficient evidence that this feature is done.

## Context

The slide-deck feature has already exposed a gap between fixture-level tests and product usefulness. A deck can pass renderer tests yet be sparse, contain marker/test prompt fragments, or fail to prove that the full gateway, model, quality, export, and browser surfaces work together. The acceptance standard for this hardening pass is therefore real full-flow behavior through the production surface, not mock output.

The user requirement is explicit: all acceptance testing for this feature must use real LLM flow, real prompts, real data, model `4omc`, gateway HTTP, quality gates, exports, and browser QA on actual exported HTML. Mock or fixture tests may remain as development guardrails, but they must not be reported as proof of done.

## Decision

1. **Acceptance evidence must be real-LLM full flow.** A slide-deck hardening slice is not done until a real generated deck passes through the gateway HTTP surface, model `4omc`, quality gates, export, HTML inspection, and browser QA.
2. **Technical guards are not acceptance.** Unit, renderer, projection, and deterministic tests may be added to protect invariants, but final reporting must distinguish them from real acceptance. A fixture pass cannot override a failed real run.
3. **The official harness uses real prompts and no marker content.** Prompts must be natural classroom requests. Generated student content must not contain smoke/test markers, raw prompt fragments, UUID scaffolding, or hidden marker strings.
4. **The acceptance suite has three core scenarios.** The baseline suite covers:
   - Grade 5 ESL/vocabulary slide deck.
   - Grade 5 math or science concept slide deck with worked example/practice.
   - Vietnamese classroom slide deck for localization/readability/chrome behavior.
5. **Each scenario is behavioral, not status-only.** Passing requires completed run status, slide-deck artifact, meaningful bounded deck structure, quality pass, standalone export, student-safe projection, no teacher-only leakage, no external assets, browser navigation, mobile readability, and print projection behavior.
6. **Failures are classified and recovered structurally.** The harness records failure type: generation sparse, quality fail, leakage, export/render fail, browser navigation fail, print fail, or infrastructure fail. The system may exercise real scoped repair/recovery where available, but must not blind-retry until green.
7. **Evidence bundles are mandatory.** Each harness run writes a timestamped evidence bundle with summary JSON, scenario inputs, endpoint/model metadata, run IDs, snapshot IDs, quality scores, export paths, assertions, copied/linked HTML, browser screenshots or QA notes, and failure artifacts when applicable.
8. **The harness is official and documented.** The real acceptance runner belongs in an official script/runbook path, not only `.scratch`. It must be CI-ready, parameterized by gateway URL/model/auth/evidence directory, and exit non-zero on any scenario failure.
9. **Real acceptance is the final gate for implementation claims.** Final implementation reports must include the real run IDs, snapshot IDs, export paths, and evidence bundle path. If the real acceptance suite is unavailable or failing, the work is not complete.

## Consequences

- Slide-deck releases will take longer to validate, but evidence will reflect actual product behavior.
- Developers can still use deterministic guards for fast iteration, but they cannot claim done from those guards alone.
- The harness becomes a reusable production-readiness tool for future slide-deck work and later CI enforcement.
- Flaky infrastructure or unavailable model endpoints block acceptance and must be reported as blockers rather than papered over.
- Evidence bundles make failures debuggable and prevent hidden regressions in content quality, projection safety, print behavior, and standalone export.

## Alternatives Considered

| Option | Pros | Cons |
|---|---|---|
| Real-LLM behavioral acceptance suite (chosen) | Proves actual product surface; catches sparse/deceptive green runs | Slower, depends on services/model availability |
| Fixture-only renderer tests | Fast and stable | Does not prove generation, quality, gateway, export, or real content usefulness |
| One real smoke scenario | Faster | Too narrow; misses subject/localization/layout variation |
| Blind retry until success | Reduces transient failures | Hides prompt/schema/recovery defects and creates false confidence |
| Manual QA only | Flexible | Not repeatable or AFK-agent friendly |

## References

- ADR-031 Full Output Test Matrix
- ADR-032 Verification Integrity and Engineering Discipline
- ADR-040 Native Slide Deck Artifact and SlideDeckEngine
- ADR-042 Slide Deck Surfaces, Quality Gates, and Release Evidence
- ADR-043 Slide Deck Display Preferences and Projection Boundaries
- `docs/testbook/runbook.md`
- `.scratch/pipeline-v2/artifacts/live_4omc_single_smoke.py`
- `services/gateway/routers/teaching_packs.py`
- `services/gateway/teaching_pack_export_writer.py`
