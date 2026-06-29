---
title: PII scrubbing for teacher requests and generated inverse-thinking cases
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Add explicit PII scrubbing around inverse-thinking inputs and outputs. Inverse-thinking cases are often based on plausible classroom mistakes; teacher prompts may include student names, class identifiers, phone numbers, or real incidents. AGENTS.md forbids student PII in content output, but the current inverse-thinking issue set does not own pre-Blueprint input scrubbing, post-Generate artifact scrubbing, or audit evidence.

## Acceptance criteria

- [ ] Teacher raw request is scrubbed before planner/content generation sees it.
- [ ] Generated inverse-thinking cases are scrubbed recursively before persistence, rendering, export, and teacher preview.
- [ ] Scrubber supports Vietnamese and English name patterns, emails, phone numbers, student IDs, school IDs, URLs, and social handles.
- [ ] Residual PII after scrubbing is a critical quality failure.
- [ ] Audit events record redaction category/count and opaque hashes only, never raw PII.
- [ ] Low-confidence PII matches are surfaced for teacher confirmation rather than silently passing.

## Detailed test suite

- [ ] `packages/quality/tests/test_pii_scrubber_vietnamese.py`: Given Vietnamese full-name examples, when scrubbed, then literal names are replaced and category counts are recorded.
- [ ] `packages/quality/tests/test_pii_scrubber_contact_info.py`: Given emails, phone numbers, URLs, and social handles, when scrubbed, then none remain in output.
- [ ] Pipeline integration test: Given a raw teacher request containing PII, when the mocked pipeline runs, then no LLM request, checkpoint state, rendered HTML, or exported file contains the original tokens.
- [ ] Audit-log test: Given a scrub event, when persisted, then it includes categories/counts/hashes and passes the scrubber itself.
- [ ] Quality-gate test: Given generated content with residual PII, when Layer 1/2 gates run, then the run fails critically with `residual_pii_detected`.
- [ ] Fixture corpus test: The canonical corpus from issue 022 contains no real PII.

## Blocked by

- .scratch/inverse-thinking/022-canonical-fixtures-and-negative-corpus.md
- .scratch/inverse-thinking/004-quality-gates-and-repair.md
