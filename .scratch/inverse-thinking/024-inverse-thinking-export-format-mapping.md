---
title: Inverse-thinking export mapping for GIFT, H5P, QTI, and Google Forms
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Define how inverse-thinking semantics survive non-HTML export formats. Existing renderer work covers standalone HTML, but the product supports GIFT, H5P, QTI, and Google Forms. Disaster-first cases, clues, safe-zone boundaries, and teacher-only rationales do not map automatically to these formats. Without explicit mapping, Layer 6 can silently produce incomplete exports.

## Acceptance criteria

- [ ] A format-support matrix documents inverse-thinking support for HTML, GIFT, H5P, QTI, and Google Forms.
- [ ] GIFT export preserves case title, disaster prompt, misconception choices, correct answer, and teacher-only rationale in allowed metadata/comment locations.
- [ ] H5P export maps inverse-thinking cases to supported H5P content types or fails with a typed unsupported-format error.
- [ ] QTI export validates against QTI 2.1 schema and preserves feedback blocks.
- [ ] Google Forms export documents/degrades unsupported partial-credit or safe-zone feedback features explicitly.
- [ ] Layer 6 export readiness fails closed when a requested format cannot preserve required inverse-thinking semantics.

## Detailed test suite

- [ ] `packages/exporters/__tests__/inverse-thinking-gift.test.ts`: Given a canonical pack, when exported to GIFT, then question count, correct answers, and teacher rationale metadata match the source pack.
- [ ] `packages/exporters/__tests__/inverse-thinking-h5p.test.ts`: Given a canonical pack, when exported to H5P or deemed unsupported, then the result is either a valid `.h5p` ZIP or a typed unsupported-format error with remediation.
- [ ] `packages/exporters/__tests__/inverse-thinking-qti.test.ts`: Given a canonical pack, when exported to QTI, then XML validates against QTI 2.1 and feedback blocks are present.
- [ ] `packages/exporters/__tests__/inverse-thinking-google-forms.test.ts`: Given a canonical pack, when mapped to Google Forms requests, then degradation warnings are emitted for unsupported feedback/partial-credit features.
- [ ] Layer 6 integration test: Given export formats `["html", "gift", "h5p"]`, when readiness runs, then unsupported or lossy mappings block export rather than silently dropping semantics.
- [ ] Round-trip test where possible: export then re-import/parse enough structure to prove case IDs and answer keys are preserved.

## Blocked by

- .scratch/inverse-thinking/001-contracts-and-canonical-pack.md
- .scratch/inverse-thinking/005-renderer-standalone-html.md
- .scratch/inverse-thinking/022-canonical-fixtures-and-negative-corpus.md
