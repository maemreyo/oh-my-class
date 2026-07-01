---
title: Surface quality gate flags in teacher approval UI
status: done
labels: [ux, quality, teacher-facing]
created: 2026-07-01
---

## What to build

The 6-layer `ArtifactQualityReport` is fully evaluated before `content_approval` gate, but the result is **not surfaced to the teacher**. The teacher approval body (`teaching-packs-gate-bodies.tsx:content_approval`) shows snapshot preview iframes but gives no signal about what the quality gate found — teachers approve or reject blind.

Wire the quality report into the gate interrupt payload and display per-layer flags in the frontend:

- **Python side:** include `ArtifactQualityReport` (or a summarised view) in the `GateInterrupt.context` JSON for `content_approval`. The field `quality_report` should carry: overall score, pass/fail, per-layer flags (fact_check uncertainty, age_check band + score, PII findings, pedagogical objective-alignment, HTML hard-blocks if any, G-Eval judge scores).
- **Frontend side:** `teaching-packs-gate-bodies.tsx` — render a collapsible quality flags panel in the `content_approval` body. Show:
  - Overall pass/fail badge with overall score
  - Per-layer indicator (green ✓ / amber ⚠ / red ✗) for: facts, age, PII, pedagogy, HTML, G-Eval
  - Expand to show detail (e.g. specific PII finding, age-band, fact-check claim uncertainty)
- Keep the existing snapshot preview iframes as-is; quality flags sit above or below them.

The quality report schema is already in `common/contracts/quality.py` — use it directly.

## Acceptance criteria

- [x] `GateInterrupt.context` for `content_approval` includes a `quality_report` field (type `ArtifactQualityReport | None`).
- [x] The frontend `content_approval` body renders per-layer quality indicators when `quality_report` is present (gracefully absent-safe — shows nothing if `None`).
- [x] A teacher can see at a glance: overall score, which layers flagged issues, and the top-level reason for each flag.
- [x] No change to approval mechanics — the quality report is informational only; the teacher still decides.
- [x] Schema parity: `quality_report` field added to the Zod-codegen'd type; FE uses the generated type.

## Detailed test suite

(Deterministic-logic tests only — no real LLM needed for this issue.)

- [x] `services/gateway/tests/test_content_approval_gate_context.py`: when `content_approval` interrupt fires, `gate_interrupt.context["quality_report"]` contains the expected `ArtifactQualityReport` shape (per-layer scores present, pass boolean, overall score).
- [x] FE unit (Vitest): `content-approval-body.test.tsx` — snapshot test that per-layer flags render; test that absent `quality_report` renders nothing extra (no crash).
- [x] Schema parity test (`scripts/verify_schema_parity.py`): `ArtifactQualityReport` Zod schema is generated and matches the Pydantic contract.

## Verification

- 2026-07-01: `uv run pytest packages/agents/tests/teaching_pack/test_content_approval_quality_flags.py -q` → `4 passed`.
- 2026-07-01: `pnpm --dir apps/web test -- content-approval-body.test.tsx` → `17 files passed`, `162 tests passed`.
- 2026-07-01: LSP diagnostics clean for `common/contracts/quality.py`.

## Blocked by

- parity-001 (done ✅) — requires quality gate to be injected
