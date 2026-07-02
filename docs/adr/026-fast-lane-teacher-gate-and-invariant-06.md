# ADR-026: Fast-Lane Teacher Gate and INVARIANT-06 Reconciliation

## Status

**Decided** (2026-07-02) — The trust-score fast-lane auto-approve at the `teacher_approval` gate is **kept** (Option A), but is made honest: it may run **only after a deterministic compliance gate passes**, it is **audited distinctly** from manual approval, it is **visibly labelled** in the UI, and it is **revertible**. INVARIANT-06 is reworded from "cannot be bypassed" to "cannot be *silently* bypassed". Companion to ADR-027 (circuit-breaker scope) and the Phase-0 gate of the agents-hardening roadmap (`docs/reports/agents/`). Resolves the #1 critical finding of Verdict 03.

## Context

A review of `packages/agents` (Verdict 00–08, 2026-07-02) found a direct semantic contradiction, confirmed against code:

- `teaching_pack/gate_trust.py` + `gate_config.py` + `teacher_memory.py` implement a trust-score **auto-approve** at the `teacher_approval` `interrupt()` gate: when a teacher's accumulated trust score is high enough, the gate is auto-resumed with `approve` **without a human pressing approve**.
- ARCHITECTURE.md §12 lists **INVARIANT-06 "Teacher Gate CANNOT be bypassed" — ✅ Enforced**.

These cannot both be true. `interrupt()` is invoked (so "enforced" holds *syntactically*), but if fast-lane resumes it with `approve` on the teacher's behalf, the gate is **functionally bypassed**. For a K-12 product where sibling invariants are safety boundaries (INVARIANT-05 answer-key isolation; `guardrail` PII middleware; hard-blocks `answer_key_leakage`/`pii_leakage`), a document claiming "✅ Enforced" while the gate can be auto-resumed is wishful documentation, not an enforced control.

Aggravating finding: deterministic compliance enforcement is **fragmented across ≥5 surfaces** — `packages/quality/layer4_judge/hard_blocks.py`, `layer3_html/html_validator.py`, `gates/presentation/answer_key_guard.py`, `config/gate_config.py`, and the `guardrail` middleware — with no single owner. So today there is **no single deterministic checkpoint** we can prove runs before any auto-approve.

## Decision

### 1. Keep fast-lane (Option A), because the UX value is real

Teachers should not have to hand-approve every provably-safe worksheet. The trust-score mechanism already exists and encodes real signal (`teacher_memory`). We keep it rather than delete it (Option B was rejected — see Alternatives).

### 2. Fast-lane is gated on a deterministic `compliance_gate_node`

Auto-approve is **only permitted** when a new deterministic, non-LLM `compliance_gate_node` (see Verdict 04 / the agents-hardening roadmap) has **passed** for the artifact. This node consolidates the fragmented enforcement (9 hard-blocks + PII + answer-key leakage) into one auditable graph step, wired **after `render_quality`, before `teacher_approval`**. If compliance fails, the artifact is **never** fast-lane eligible and must be seen by a human — fail-closed.

Ordering (authoritative): `render_quality` (subjective LLM judge) → `compliance_gate_node` (deterministic policy) → `teacher_approval` (human gate, fast-lane eligible only if compliance passed).

### 3. Auto-approve is audited distinctly from manual approve

The existing `teacher_audit_log` middleware must record fast-lane approvals with an explicit, distinguishable record — e.g. `{"decision": "auto_approved", "via": "fast_lane", "trust_score": 9.2, "compliance_passed": true}` — never merged into or indistinguishable from a manual `approve`.

### 4. Auto-approve is visible and revertible

- The gate UI must render an explicit label for auto-approved artifacts (e.g. "✓ Auto-approved — trust 9.2/10 · View details") that is visually distinct from a manually-approved artifact, with a "View details" affordance exposing `judge_rationale` + `healing_history` (Verdict 07).
- A **revert window** must exist: the teacher can undo a fast-lane approval before the downstream `export_finalize` materialises, restoring the artifact to a pending-manual state.

### 5. INVARIANT-06 is reworded and given a real test

New wording:

> **INVARIANT-06** — The Teacher Gate cannot be **silently** bypassed. Trust-score auto-approval is an audited, visibly-labelled, revertible decision that is permitted **only after `compliance_gate_node` passes**.

This invariant gets a dedicated test in `tests/invariants/` (per Verdict 06) asserting: (a) auto-approve cannot occur when compliance failed; (b) every auto-approve emits a distinguishable audit record; (c) a revert path exists before export.

## Consequences

- The documented ✅ for INVARIANT-06 becomes true — an enforced control, not an aspiration.
- Fast-lane's blast radius is bounded by a deterministic safety floor: no artifact reaches a student via auto-approve without passing PII/answer-key/hard-block checks.
- `compliance_gate_node` becomes a hard dependency of this ADR (Phase 3 of the roadmap); fast-lane's auto-resume path must not ship before it.
- Teachers gain visibility into *what they are trusting*, building trust rather than assuming it (Verdict 07).
- Intersects the in-flight ADR-018 parity work (6-layer quality / healing wiring); the compliance consolidation must be reconciled with `SixLayerQualityGate` so PII/answer-key checks are not duplicated across the judge and the compliance node.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| **A — Keep fast-lane, gate on compliance + audit + label + revert (chosen)** | Retains real UX value; makes the invariant honest; deterministic safety floor | Requires `compliance_gate_node` before auto-resume can ship |
| B — Remove fast-lane entirely | Cleanest invariant; zero bypass surface | Discards built trust-score investment; every artifact needs manual approve → friction; must be offset by explainable-gate UX anyway |
| Keep fast-lane as-is, only reword the invariant | Least work | Leaves an unaudited, invisible bypass in a K-12 safety path — rejected |
