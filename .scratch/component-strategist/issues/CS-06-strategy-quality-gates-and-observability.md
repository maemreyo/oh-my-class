---
title: Add strategy quality gates and observability ledger
status: ready-for-agent
labels: [component-strategist, quality, observability]
created: 2026-07-05
---

## Parent

ADR-035 and ADR-036.

## What to build

Add a pre-generation final-strategy gate and a post-generation component-fill gate. The gates reject technically valid but pedagogically weak or unsafe strategies, and they emit structured observability events for provisional hypotheses, research-signal application, candidate filtering, scoring, diversity adjustment, fallback, variant selection, teacher feedback application, and append-only revisions.

The teacher sees a compact rationale. Developers and QA get an inspectable event trail and optional debug ledger.

## Acceptance criteria

- [ ] Pre-generation gate rejects unsupported component type, non-renderable selected component, missing required learning move, missing objective coverage, invalid sequence order, invalid slot budgets, prose-only strategy, no retrieval/formative check, all components same family without documented exception, Bloom/MOET mismatch, artifact/export incompatibility, teacher-only field on student surface, and fallback without reason.
- [ ] Post-generation gate verifies generated artifacts filled selected ordered slots, preserved selected learning moves/components, respected fill requirements/budgets/audience policies, and did not reorder/downgrade to unsupported/prose-only output.
- [ ] Generic slot validator verifies slot ID, component type, objective refs, audience policy, budget caps, projection status, export constraints, and lineage markers.
- [ ] Per-learning-move/component validators verify pedagogy-specific requirements such as misconception-mapped distractors, worked-example steps, retrieval affordances, MOET true/false scoring, and answer-key separation.
- [ ] Validator registry supports category, severity, priority, deterministic ordering, version tracking, and typed issue outputs; no central if/elif chain dispatches validators.
- [ ] Every production learning move has at least declarative fill-validation policy; missing required validators fail validation/gates.
- [ ] Soft warnings cover low diversity, low engagement, high cognitive load, too many high-complexity components, weak UDL coverage, and teacher preference conflicts.
- [ ] Observability events include request fingerprint, provisional hypotheses, typed research signals applied, hard-filtered candidates, rejected candidates/reasons, top candidate score breakdowns, diversity adjustments, teacher-memory multipliers, fallback path, revision lineage, latency, and cache hit/miss where relevant.
- [ ] Optional debug ledger can be enabled without changing teacher-facing payload or leaking PII.
- [ ] Tests cover every hard reject, representative warnings, event emission, and no-PII/debug-ledger behavior.

## Blocked by

- CS-03 selector, scorer, and diversity core.
- CS-05 Content Creator fills selected components.

## References

- `docs/adr/036-component-strategy-knowledge-and-governance.md`
- `packages/agents/teaching_pack/quality.py`
- `packages/agents/teaching_pack/quality_routing.py`
- `packages/agents/teaching_pack/quality_runtime.py`
- `packages/quality/compliance_policy.py`
- `packages/agents/events.py`
- `packages/renderer/src/agent-component-projection.ts`

## Implementation notes

- Fail closed for invalid knowledge/renderability/compliance. Graceful fallback is allowed only for missing personalization, LLM polish failure, or unavailable variants.
- Do not put full ledgers in the teacher approval UI.
- LLM critique is advisory only; deterministic gates define strategy validity.
- Follow ADR-038 for validator composition and rendered-output lineage gates.
