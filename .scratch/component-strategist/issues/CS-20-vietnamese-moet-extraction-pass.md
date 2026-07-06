---
title: Add Vietnamese/MOET extraction pass for launch cohort
status: ready-for-agent
labels: [component-strategist, vietnamese, knowledge-db]
created: 2026-07-06
---

## Parent

`.omo/ulw-research/20260706-103328-component-strategist-web/ROUGH-REPORT-verdicts-and-direction.md`

## What to build

Extract the Vietnamese/MOET curriculum and assessment facts needed for the initial public launch cohort into reviewed strategy knowledge. The extracted knowledge should be scoped by grade/subject and should encode objective, terminology, and assessment differences that the strategist and validators can consume deterministically.

This slice turns the legal/curriculum anchors from the report into product-scoped knowledge. It should not claim complete national coverage beyond the launch cohort.

## Acceptance criteria

- [ ] Launch-cohort grade/subject scope is explicit in the extracted knowledge.
- [ ] Knowledge encodes relevant `Yêu cầu cần đạt` objective anchors for the launch cohort.
- [ ] Knowledge distinguishes `Tiếng Việt` primary usage from `Ngữ văn` secondary usage where relevant.
- [ ] Knowledge encodes primary-vs-secondary assessment differences without copying secondary scoring assumptions into primary flows.
- [ ] Knowledge encodes the Vietnamese assessment taxonomy used by the strategist for relevant launch-cohort contexts.
- [ ] Tests prove unsupported grade/subject combinations do not receive unsupported MOET-compliant claims.

## Blocked by

- CS-02 YAML knowledge DB and SQLite index.
- CS-12 blueprint objective normalization and strategy lineage.
- CS-13 delivery, assessment, budget, and slot-fill contracts.
