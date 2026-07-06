---
title: Add MOET validator and public-compliance QA gate
status: ready-for-agent
labels: [component-strategist, vietnamese, quality]
created: 2026-07-06
---

## Parent

`.omo/ulw-research/20260706-103328-component-strategist-web/ROUGH-REPORT-verdicts-and-direction.md`

## What to build

Add deterministic validation and QA gating for public/default MOET-compliant Component Strategist launch. The validator should check that selected objectives, strategy slots, assessment intent, scoring constraints, and terminology stay inside the extracted Vietnamese/MOET scope.

This slice is the public-compliance gate after extraction. It should fail closed when a run claims MOET compliance but lacks scoped support.

## Acceptance criteria

- [ ] Validator rejects MOET-compliant claims for unsupported grade/subject/scope combinations.
- [ ] Validator checks that objective refs can map to extracted `Yêu cầu cần đạt` anchors when MOET compliance is claimed.
- [ ] Validator checks assessment/scoring intent against the extracted primary/secondary constraints.
- [ ] Validator checks Vietnamese taxonomy and terminology assumptions for supported launch-cohort cases.
- [ ] Public release gate includes a sampled Vietnamese/MOET QA path before default enablement.
- [ ] Tests cover pass, fail-closed unsupported scope, primary/secondary assessment mismatch, and claim-guard interaction.

## Blocked by

- CS-06 strategy quality gates and observability.
- CS-13 delivery, assessment, budget, and slot-fill contracts.
- CS-20 Vietnamese/MOET extraction pass.
