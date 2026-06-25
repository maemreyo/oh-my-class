---
title: "Full flow 07 - Artifact retrieval and web preview"
status: ready-for-agent
labels: [ready-for-agent, full-flow, partial-implementation, security]
created: 2026-06-25
reviewed: 2026-06-25
---

## Review status

**Partial implementation exists, but authorization and UI coverage are incomplete.** Artifact list/detail endpoints exist and redact sections marked `teacher_only`. They do not enforce run ownership, and tests seed runs directly instead of exercising generated artifacts through the full flow.

Known current implementation:

- `services/gateway/routers/artifacts.py` exposes list and detail endpoints.
- `_extract_artifacts_from_state()` generates fallback ids by list index.
- `_redact_teacher_only()` removes sections with `teacher_only: true`.
- `apps/web/src/hooks/use-artifact.ts` can fetch artifacts.
- `apps/web/src/components/artifact-preview.tsx` renders `rendered_html` in an iframe, but run detail does not yet clearly wire artifact list/selection/export preview end-to-end.

## Remaining work

- [ ] Use the shared run access helper from Issue 02 for all artifact endpoints.
- [ ] Preserve stable artifact ids from generation; avoid index-derived ids as the primary identity once artifacts are generated.
- [ ] Redact all teacher-only material, including nested answer keys in metadata, accessibility, teacher-only artifact types, or other parseable fields, not only top-level sections.
- [ ] Decide whether artifact preview returns raw `ArtifactContent`, rendered HTML, or both, and align frontend types accordingly.
- [ ] Wire the run detail page to list artifacts and render a selected artifact preview from real API data.

## Acceptance criteria

- [ ] `GET /run/{run_id}/artifacts` returns the artifacts generated for that visible run.
- [ ] `GET /run/{run_id}/artifacts/{artifact_id}` returns one artifact with content and metadata.
- [ ] Unknown run/artifact returns structured 404.
- [ ] Unauthorized run/artifact access returns structured 403.
- [ ] Artifact responses do not leak hidden teacher-only answers into student preview fields, including nested fields.
- [ ] Web run detail renders artifact list and a selected artifact preview.
- [ ] Loading/error/empty states are handled in the UI.
- [ ] `make check` passes.

## Test suite upgrades

- [ ] Unit: artifact response mapper preserves metadata and redacts/segments teacher-only fields correctly.
- [ ] Unit: nested answer-key/teacher-only data is removed from student preview responses.
- [ ] Integration: generated run artifacts can be listed and fetched individually.
- [ ] Integration: artifact from another teacher cannot be fetched by unauthorized teacher.
- [ ] Integration: unknown artifact returns 404.
- [ ] Frontend test: run detail renders artifact list from API-provided content.
- [ ] Frontend test: artifact preview renders selected API-provided content and handles empty `rendered_html` safely.
- [ ] Frontend test: artifact preview shows error state when endpoint returns failure.
- [ ] Real surface: `curl GET /run/{id}/artifacts`, then open web run detail and verify preview is visible.

## Blocked by

- Full flow 06 - Generate draft teaching artifacts
