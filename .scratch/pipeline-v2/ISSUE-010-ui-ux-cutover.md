---
title: Pipeline V2 frontend UI/UX cutover
status: ready-for-agent
labels: [pipeline-v2, frontend, ui-ux, gates]
created: 2026-06-27
order: 10
blocked_by: [ISSUE-003-control-plane-executor, ISSUE-004-run-contract-setup-stage, ISSUE-008-rendered-preview-approval]
adr_refs:
  - docs/adr/003-run-contract-and-conditional-hitl.md
  - docs/adr/005-generic-gate-resume-api.md
  - docs/adr/008-artifact-workflow-and-rendered-snapshots.md
---

## Problem

The current UI assumes two approval gates and renders JSON in a modal. Pipeline V2 needs user-centric gates, stage progress, artifact progress, search/contract confirmation, and rendered HTML approval.

## Scope

Cut frontend over to V2 APIs and UX.

Agent-ready tasks:

1. Update run creation types/hooks for V2 request and response models.
2. Add stage/status progress UI mapped to V2 state machine.
3. Implement `GateModalShell` with gate registry mapping.
4. Implement gate bodies: `ClarificationGateBody`, `ContractConfirmationBody`, `SearchPlanConfirmationBody`, `BlueprintApprovalBody`, and `ContentApprovalBody`.
5. Implement generic `/resume` client hook.
6. Implement artifact progress components using persisted events/status.
7. Implement rendered preview tabs per artifact with student/teacher view controls.
8. Implement scoped rejection UX by artifact/section.
9. Ensure SSE reconnect/replay UX works after refresh.
10. Update error and loading states for background execution.

## Out Of Scope

- Major visual redesign unrelated to V2 workflow.
- Admin config UI.
- Non-core artifact/export UI.

## Acceptance Criteria

- Teacher can create a V2 run and see queued/running/stage progress.
- Teacher can answer clarification, confirm/edit contract, confirm/edit search plan, approve/edit/reject blueprint, and approve/request changes on rendered content.
- Approval UI no longer dumps raw JSON as primary UX.
- Artifact progress and quality statuses are visible.
- Refreshing the page recovers state through persisted run status and SSE replay.
- Mobile-ish viewport remains usable for gate dialogs.

## Test Plan

- Component tests for every gate body.
- Hook tests for create run, resume, run status, event replay, and artifact preview retrieval.
- Browser QA for complete teacher journey.
- Accessibility checks for modal focus, labels, and keyboard actions.

## Observability

- Client logs should include run id, gate, action, and request id without sensitive content.
- UI should surface user-friendly errors from failed gates or run failures.

## Required Edge Cases And Tests

- UI handles queued, running, awaiting clarification, awaiting contract confirmation, awaiting search confirmation, awaiting blueprint approval, generating, healing, preview ready, awaiting content approval, exporting, completed, failed, cancelled, escalated, and timed out statuses.
- Double-click primary gate action sends one idempotent resume request.
- Stale gate modal after another tab resumes shows conflict/current status, not silent success.
- SSE disconnect/reconnect and page refresh recover state and missed events.
- Gate bodies validate required fields before submit and show backend validation errors clearly.
- Contract gate shows inferred values and reasons.
- Search gate shows query plan, source policy, budget, and estimated work.
- Blueprint approval renders teacher-friendly plan, not raw JSON.
- Content approval renders artifact tabs, quality badges, student/teacher preview toggle, and scoped rejection controls.
- Soft-deleted/cancelled runs disappear or show revoked state appropriately.
- Accessibility tests cover keyboard navigation, focus trap, labels, modal close, and screen-reader names.
- Responsive tests cover mobile-ish viewport for every gate body.

## Rollback

V2 UI cutover is tied to V2 backend cutover. If incomplete, keep V2 unreleased rather than exposing mixed V1/V2 workflow.
