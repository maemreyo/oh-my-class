---
title: "Full flow 10 - Export and finalize downloadable teaching pack"
status: ready-for-agent
labels: [ready-for-agent, full-flow, incomplete, export]
created: 2026-06-25
reviewed: 2026-06-25
---

## Review status

**Partial implementation exists, but export readiness/finalization is not complete and can violate hard invariants.** A simple HTML renderer and export download endpoints exist. Export readiness does not fully validate requested formats, the renderer does not fail closed on `http(s)://` content, and tests mostly preseed exported files instead of proving finalization.

Known current implementation:

- `packages/agents/nodes/finalize.py` renders simple standalone HTML and skips top-level `teacher_only` artifacts.
- `services/gateway/routers/runs.py` exposes `/exports` list and `/exports/{artifact_id}` download endpoints.
- `packages/agents/gates/export_readiness.py` checks only non-empty artifacts/export formats and optional judge score threshold.
- `packages/quality/layer6_export/export_validator.py` still has TODOs for multi-judge validation and only checks basic format requirements.
- A probe showed `_render_artifact_to_html()` preserves `https://...` text in exported HTML; it does not enforce the no-external-reference invariant.

## Remaining work

- [ ] Implement export readiness against requested formats and available artifact types, including unsupported-format typed errors.
- [ ] Decide supported MVP export formats. If only HTML is supported now, reject GIFT/H5P/QTI with typed validation instead of silently ignoring them.
- [ ] Run the presentation contract on final HTML and fail closed on `http(s)://` references, missing DOCTYPE, missing viewport, missing brand, unmanaged JS, native radio inputs, or answer-key leakage.
- [ ] Exclude all teacher-only answer material from student exports, including nested teacher-only sections and answer-key artifacts unless exporting teacher-only output explicitly.
- [ ] Persist exported files with stable ids, run id, format, artifact metadata, content type, and retrievable content/location.
- [ ] Apply ownership guard to export list/download endpoints.
- [ ] Add web completed-run export/download UI.
- [ ] Add one true full-flow E2E with mocked LLMs: create -> approve blueprint -> generate/quality -> approve content -> export -> download.

## Acceptance criteria

- [ ] Export readiness validates requested formats against available artifacts and blocks missing required artifacts.
- [ ] Unsupported export format returns a typed validation error.
- [ ] Finalize step renders standalone HTML and any requested supported export formats.
- [ ] Exported HTML passes the presentation contract and contains no `http://` or `https://` references.
- [ ] Exported files are persisted with run id, format, artifact metadata, content type, and retrievable location/content.
- [ ] Gateway exposes export list/download endpoints only for visible runs.
- [ ] Web displays completed run state and downloadable/export-previewable outputs.
- [ ] Completed run remains readable after refresh within the configured persistence mode.
- [ ] `make check` passes.

## Test suite upgrades

- [ ] Unit: export readiness passes/fails according to format requirements.
- [ ] Unit: unsupported export format returns a typed validation error.
- [ ] Unit: finalize renderer creates standalone HTML with DOCTYPE, viewport, no external references, and brand string.
- [ ] Unit: finalize fails or removes output when artifact content contains `http://` or `https://` references.
- [ ] Unit: teacher-only sections and answer-key artifacts are excluded from student export.
- [ ] Integration: approved run finalizes to completed status with at least one exported file through real graph resume.
- [ ] Integration: exported HTML passes presentation contract checks.
- [ ] Integration: download endpoint returns correct content type/body for exported file.
- [ ] Integration: another teacher cannot list or download exports for a run they do not own.
- [ ] Frontend test: completed run shows export/download action.
- [ ] E2E surface: create run -> approve blueprint -> approve content -> download final output; verify HTTP 200 and saved file contains standalone HTML.

## Blocked by

- Full flow 09 - Content approval and regeneration resume graph
