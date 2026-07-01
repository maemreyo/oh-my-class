---
title: Semantic anchoring quality gate and review status
status: done
labels: [ready-for-agent, quality, safety]
created: 2026-07-01
---

## What to build

Add a per-cluster SemanticAnchoringQualityGate that returns `passed`, `needs_review`, or `failed`. It evaluates lexical correctness, anchor quality, pedagogical usability, projection safety, and standalone HTML invariants.

This gate reuses existing quality layers where possible, but applies them to vocabulary cluster contracts and projections. It must fail hard on student leakage and external assets, and use `needs_review` for uncertainty that is teacher-actionable.

## Acceptance criteria

- [x] Gate produces structured verdicts with issue severity, layer, evidence, and recommended action.
- [x] Lexical uncertainty or edge-case nuance can mark a cluster `needs_review` without blocking the whole run.
- [x] Student projection leakage or answer-key leakage marks the cluster `failed` and withholds student export.
- [x] Placeholder content, unsupported external assets, and invalid schema are hard failures.
- [x] Quality results are written to the per-cluster evidence ledger and teacher-facing status payload.

## Detailed test suite

- [x] `packages/quality/tests/test_semantic_anchoring_quality_gate.py`: passed cluster returns `passed` with evidence.
- [x] `packages/quality/tests/test_semantic_anchoring_quality_gate.py`: lexical uncertainty returns `needs_review`.
- [x] `packages/quality/tests/test_semantic_anchoring_projection_safety.py`: teacher-only notes in student projection hard-fail.
- [x] `packages/quality/tests/test_semantic_anchoring_html_invariants.py`: external asset references hard-fail.
- [x] Regression: existing 6-layer quality tests pass unchanged for this slice via additive package only.

## Verification

- `uv run pytest packages/quality/tests/test_semantic_anchoring_quality_gate.py packages/quality/tests/test_semantic_anchoring_projection_safety.py packages/quality/tests/test_semantic_anchoring_html_invariants.py -q` → `4 passed`.
- LSP diagnostics clean for `packages/quality/semantic_anchoring/gate.py` and focused tests.

## Blocked by

- `005-semantic-anchor-synthesis.md`
- `006-practice-generator-capability.md`
