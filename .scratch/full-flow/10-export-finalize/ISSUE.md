---
title: "Full flow 10 - Export and finalize downloadable teaching pack"
status: ready-for-agent
labels: [ready-for-agent, full-flow]
created: 2026-06-25
---

## What to build

Complete the run by validating export readiness, rendering/exporting approved artifacts, persisting exported files, and exposing them to the web for download or preview. This replaces the finalize dummy node with real behavior.

This slice is done when a teacher can create a run, approve both gates, and obtain final standalone HTML/export outputs from the web.

## Acceptance criteria

- [ ] Export readiness validates requested formats against available artifacts and blocks missing required artifacts.
- [ ] Finalize step renders standalone HTML and any requested supported export formats.
- [ ] Exported files are persisted with run id, format, artifact metadata, and retrievable location/content.
- [ ] Gateway exposes export list/download endpoint or includes exported files in run detail response.
- [ ] Web displays completed run state and downloadable/export-previewable outputs.
- [ ] Completed run remains readable after refresh within the configured persistence mode.
- [ ] `make check` passes.

## Test suite

- [ ] Unit: export readiness passes/fails according to format requirements.
- [ ] Unit: finalize renderer creates standalone HTML with DOCTYPE, no external assets, and brand string.
- [ ] Unit: unsupported export format returns a typed validation error.
- [ ] Integration: approved run finalizes to completed status with at least one exported file.
- [ ] Integration: exported HTML passes presentation contract checks.
- [ ] Integration: download endpoint returns correct content type/body for exported file.
- [ ] Frontend test: completed run shows export/download action.
- [ ] E2E surface: create run -> approve blueprint -> approve content -> download final output; verify HTTP 200 and saved file contains standalone HTML.

## Blocked by

- Full flow 09 - Content approval and regeneration resume graph
