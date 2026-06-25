---
title: "Full flow 07 - Artifact retrieval and web preview"
status: ready-for-agent
labels: [ready-for-agent, full-flow]
created: 2026-06-25
---

## What to build

Expose generated draft artifacts through the gateway and render them in the web run detail page. A teacher should be able to open a run and preview the generated artifacts before content approval.

This slice completes the read path for generated content but does not finalize exports.

## Acceptance criteria

- [ ] `GET /run/{run_id}/artifacts` returns the artifacts generated for that run.
- [ ] `GET /run/{run_id}/artifacts/{artifact_id}` returns one artifact with content and metadata.
- [ ] Unknown run/artifact returns structured 404.
- [ ] Artifact responses do not leak hidden teacher-only answers into student preview fields.
- [ ] Web run detail renders artifact list and a selected artifact preview.
- [ ] Loading/error/empty states are handled in the UI.
- [ ] `make check` passes.

## Test suite

- [ ] Unit: artifact response mapper preserves metadata and redacts/segments teacher-only fields correctly.
- [ ] Integration: generated run artifacts can be listed and fetched individually.
- [ ] Integration: artifact from another teacher cannot be fetched by unauthorized teacher.
- [ ] Integration: unknown artifact returns 404.
- [ ] Frontend test: artifact preview renders API-provided content.
- [ ] Frontend test: artifact preview shows error state when endpoint returns failure.
- [ ] Real surface: `curl GET /run/{id}/artifacts`, then open web run detail and verify preview is visible.

## Blocked by

- Full flow 06 - Generate draft teaching artifacts
