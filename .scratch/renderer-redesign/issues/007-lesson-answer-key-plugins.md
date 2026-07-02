---
title: Migrate lesson and answer_key plugins with audience safety
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Migrate `lesson` and `answer_key` into plugins with explicit audience policies. Student lesson rendering must strip teacher-only data; answer key rendering must remain controlled and never appear through a student lesson path.

## Acceptance criteria

- [ ] `lesson` and `answer_key` plugins declare complete plugin metadata, schemas, capabilities, and sanitizer policies.
- [ ] Student `lesson` output removes teacher-only fields and passes leak-prevention invariants.
- [ ] `answer_key` plugin declares appropriate audience support and sanitizer policy.
- [ ] Existing paper-dossier lesson/answer-key behavior is represented as plugin behavior or intentionally superseded by the new plugin design.
- [ ] Golden snapshots cover teacher/student-relevant cases and print where supported.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 004-quiz-tracer-plugin.md
- 005-practice-plugins.md
