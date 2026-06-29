---
title: Pipeline V2 frontend UI/UX cutover
status: review-partial
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

## Ultrawork Review — 2026-06-27

Status: REVIEW-PARTIAL. Active Teaching Pack frontend components/hooks are present with component tests, and responsive browser QA for the live run-detail/list/approvals surfaces is now proven. Full accessibility/focus-trap QA and complete teacher-journey browser coverage remain broader release work.

Active-surface reconciliation: the historical review below names `pipeline-v2-*` frontend components/hooks. Current UI/browser QA must target the Teaching Pack dashboard flow and active `/teaching-packs/*` API/SSE routes. Do not add old `/pipeline-v2/*` client paths or compatibility hooks.

Evidence:
- V2 UI additions include `apps/web/src/hooks/use-pipeline-v2.ts`, `pipeline-v2-stage-progress.tsx`, `pipeline-v2-gate-shell.tsx`, `pipeline-v2-artifact-progress.tsx`, `pipeline-v2-scoped-rejection.tsx`, and changes to `apps/web/src/app/(dashboard)/runs/[runId]/page.tsx` and `apps/web/src/lib/api-client.ts`.
- Tests cover hooks and components in `apps/web/tests/hooks.test.ts`, `apps/web/tests/pipeline-v2-components.test.tsx`, and `apps/web/tests/pipeline-v2-artifacts.test.tsx`.
- UI status/gate/artifact progress surfaces are backed by the V2 API/event model from Issues 003 and 008.
- Active UI/CORS browser QA evidence, 2026-06-29: `.scratch/pipeline-v2/artifacts/live-v2-ui-ux-browser-qa-2026-06-29.json` records passing Playwright coverage for run `231401e0-9ac8-49ef-afab-e6bf91579b69` across `/runs/{runId}`, `/runs`, and `/approvals`; screenshots are persisted at `live-v2-ui-ux-desktop/tablet/mobile/runs-list/approvals-2026-06-29.png`.
- Browser QA passed desktop `1280x900`, tablet `768x900`, and mobile `375x812` with `loadedRunDetail=true`, progress visible, gate/event UI visible, no gateway-unavailable state, no console errors, and `showsHorizontalOverflow=false` at every breakpoint.
- Runtime CORS preflight for active Teaching Pack routes was fixed by making `CORSMiddleware` outermost relative to auth middleware; `services/gateway/tests/test_main.py` covers unauthenticated preflight to Teaching Pack routes.
- Responsive overflow fixes landed in the active dashboard shell and run/gate detail surfaces: `apps/web/src/app/(dashboard)/layout.tsx`, `apps/web/src/app/(dashboard)/runs/[runId]/page.tsx`, and `apps/web/src/components/teaching-packs-gate-shell.tsx`.
- Content approval preview toggle is now directly regression-tested on the active gate body. `apps/web/tests/teaching-packs-components.test.tsx` renders `TeachingPackGateBody` for `content_approval` and asserts both `Student view` and `Teacher view` controls plus the default student preview iframe URL are present; `snapshotPreviewUrl` coverage also proves teacher preview URL construction.
- Evidence: `pnpm --filter @oh-my-class/web test -- teaching-packs-components.test.tsx` → 7 files / 96 tests passed; `pnpm --filter @oh-my-class/web typecheck` → passed.
- SSE reconnect/replay is now directly regression-tested for the active Teaching Pack hook. `apps/web/tests/teaching-pack-status-sse.test.ts` stubs `EventSource`, receives `teaching_pack.content_approval.opened` with `lastEventId=42`, triggers `onerror`, advances the reconnect timer, and asserts the next connection URL includes `?last_event_id=42` with credentials enabled.
- Evidence: `pnpm --filter @oh-my-class/web test -- teaching-pack-status-sse.test.ts` → 8 files / 97 tests passed; `pnpm --filter @oh-my-class/web typecheck` → passed.
- Search-plan and blueprint gate bodies now render teacher-readable summaries instead of making raw JSON the primary UX. `SearchPlanSummary` surfaces reason, estimated work, budget, query list, and source policy; `BlueprintSummary` surfaces topic, grade, subject, duration, learning objectives, and assessment checkpoints.
- Evidence: `apps/web/tests/teaching-pack-gate-bodies-render.test.tsx` renders both active gate bodies and asserts readable labels/content are present while raw JSON key dumps such as `&quot;query_plan&quot;` and `&quot;learning_objectives&quot;` are absent from the primary view. `pnpm --filter @oh-my-class/web test -- teaching-pack-gate-bodies-render.test.tsx` → 9 files / 99 tests passed; `pnpm --filter @oh-my-class/web typecheck` → passed.

Gaps:
- Browser QA for the full teacher journey, accessibility focus/keyboard behavior, and SSE reconnect after refresh remains release work beyond the responsive run-detail/list/approvals proof above.
- Component names indicate generic gate shell/scoped rejection support, but not all named gate bodies from the original scope are independently proven.
- The active Teaching Pack SSE hook now has direct client-side replay/reconnect proof for `last_event_id`; remaining SSE work is full browser refresh/reconnect QA, not hook behavior.
- Rendered preview URL helpers and active content-approval gate UI now have direct component evidence for student/teacher preview controls; remaining preview work is browser/manual QA of the rendered iframe content itself.
- Search-plan and blueprint gate bodies now have structured-view regression coverage. Remaining gate-body proof is full browser/a11y interaction QA, not primary rendering shape.
