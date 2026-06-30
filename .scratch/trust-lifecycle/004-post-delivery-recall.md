---
title: Post-delivery content recall and incident handling
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

A recall path for when defective/harmful content slips past the pre-delivery gates and reaches students. Pre-delivery safety is strong, but there is currently no takedown.

- **Recall action**: mark a delivered pack/artifact `recalled` → **revoke access** (close the Google Form responder, mark the rendered snapshot revoked) → **notify the teacher** (optionally guardians). Reuse ADR-012's "revoke access immediately" + soft-delete.
- **Triggers**: teacher-initiated (primary, fast); a post-hoc **re-scan hook** when safety rules update (re-scan already-delivered content); and production-trace-feedback (testing/007) pattern detection.
- **Blast-radius + audit**: use `DeliveryRecord` (effectiveness-loop 001) to identify affected students/deliveries; log the recall to `TeacherAuditLog`; **invalidate KT attempts** computed from recalled content so the effectiveness loop never learns from defective material.

## Acceptance criteria

- [ ] A recall flips the artifact/run to `recalled`, revokes the digital delivery, and notifies the teacher.
- [ ] Recall can be triggered by the teacher, a safety-rule re-scan, or trace-feedback.
- [ ] Affected students/deliveries are identified via `DeliveryRecord`; the recall is audit-logged.
- [ ] KT attempts derived from recalled content are invalidated/flagged.

## Detailed test suite

(Real DB.)

- [ ] `services/gateway/tests/test_recall_action.py`: a recall revokes access (Google Form closed, snapshot revoked) and notifies; the pack shows `recalled`.
- [ ] `services/gateway/tests/test_recall_blast_radius.py`: affected deliveries are enumerated from `DeliveryRecord`; recall is audit-logged.
- [ ] `services/gateway/tests/test_recall_kt_invalidation.py`: KT attempts from recalled content are invalidated and excluded from mastery.
- [ ] Run `uv run pytest services/gateway/tests/test_recall_*.py -v`.

## Blocked by

- .scratch/effectiveness-loop/001-outcome-model-and-privacy-foundation.md
