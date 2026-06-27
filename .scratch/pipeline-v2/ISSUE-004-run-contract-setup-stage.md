---
title: Pipeline V2 RunContract, smart preflight, and setup HITL gates
status: ready-for-agent
labels: [pipeline-v2, run-contract, hitl]
created: 2026-06-27
order: 4
blocked_by: [ISSUE-001-foundation-architecture, ISSUE-002-production-persistence, ISSUE-003-control-plane-executor]
adr_refs:
  - docs/adr/003-run-contract-and-conditional-hitl.md
  - docs/adr/005-generic-gate-resume-api.md
---

## Problem

Preflight and Quickstart are too weak. They do not prevent ambiguous or incomplete requests from reaching expensive LLM stages, and they do not freeze resolved execution policy into a reproducible contract.

## Scope

Implement the V2 `setup_contract` stage.

Agent-ready tasks:

1. Define public RunContract and ContractRevision contracts.
2. Implement smart deterministic Preflight for runnable request validation.
3. Implement diagnostic mode decision: `generate_pack` default, `diagnose_then_generate` only with student evidence.
4. Implement Quickstart config resolution from code defaults, YAML policy, `.env`, request overrides, and teacher-confirmed values.
5. Persist RunContract current revision and append-only revisions.
6. Implement `clarification_required` gate payloads for hard missing request fields.
7. Implement `contract_confirmation` gate payloads for risky defaults and important inferred values.
8. Add localization/curriculum hooks: locale, instruction language, curriculum, grade band, subject, citation locale preference.
9. Ensure downstream stages read RunContract snapshot rather than raw env/YAML for business decisions.

## Out Of Scope

- Admin runtime config UI.
- Full diagnostician implementation.
- Research Engine behavior after setup.

## Acceptance Criteria

- Missing topic, grade/class band, subject, or unsupported artifact/export combo does not call Planner.
- Safe defaults are applied without unnecessary HITL.
- Risky defaults produce contract confirmation.
- Contract revisions are append-only and auditable.
- Config version/hash is stored in the contract.
- Curriculum defaults are optional and confirmed only when high-impact or ambiguous.

## Test Plan

- Contract validation unit tests.
- Preflight tests for missing/ambiguous/unsupported inputs.
- Integration tests for clarification and contract confirmation gates through `/resume`.
- Persistence tests for revision history.

## UX Notes

- Contract confirmation UI should show inferred fields and why they were inferred.
- Clarification should ask focused questions, not dump technical errors.

## Required Edge Cases And Tests

- Missing raw request, grade, subject, topic, language ambiguity, unsupported artifact type, unsupported export format, and empty class info are handled before Planner.
- Safe defaults do not trigger unnecessary gates.
- Risky defaults trigger contract confirmation with explanation.
- Diagnosis mode without student evidence triggers clarification or contract correction, not a fake diagnosis.
- Student evidence with PII is minimized and not sent to search.
- Mixed-language request prompts language/curriculum confirmation when output language is ambiguous.
- Curriculum defaulting handles `vi-VN` math, English ESL, and unknown locale.
- Contract revision history is append-only and records actor/source/reason/effective stage.
- Downstream stages cannot mutate contract directly; attempted mutation must become a change request.
- Config version/hash is persisted and differs when policy YAML changes.
- Tests cover teacher edit of contract, cancelled contract gate, stale contract gate response, and admin override.

## Rollback

Keep the stage behind V2 cutover until the setup gates are stable. No V1 preservation required after V2 cutover.
