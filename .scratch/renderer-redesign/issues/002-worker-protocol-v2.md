---
title: Renderer worker protocol V2 with typed responses
status: completed
labels: []
created: 2026-07-02
completed: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Upgrade the Python↔Node renderer boundary to send `WorkerRenderRequest` payloads and receive typed success/failure responses from the new renderer kernel. Keep stdin/stdout transport, but include `requestId`, `kind`, `input`, `context`, manifest, diagnostics, metrics, and typed retryable errors.

## Acceptance criteria

- [x] Node worker accepts `{ requestId, kind, input, context }` and calls the new `render()` API.
- [x] Successful worker responses include `{ ok: true, html, manifest, diagnostics, metrics }`.
- [x] Failure responses include typed error `code`, `category`, `retryable`, `message`, and optional details.
- [x] Python pool honors `retryable` and does not retry validation, unknown-kind, unsupported-audience, asset-policy, sanitizer, or template-not-found errors.
- [x] Contract tests cover valid render, malformed JSON, version mismatch, unknown kind, validation error, retryable internal error, and timeout.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 001-core-renderer-kernel.md

## Implementation

- Added worker protocol V2 handling in `packages/renderer/src/agent-worker.ts` while preserving the legacy worker request shape.
- Added typed worker success and failure envelopes backed by `RendererError` codes/categories/retryability.
- Added `RendererPool.render_v2()` and typed `WorkerRenderRequest`/`RenderContext` request models in `services/gateway/renderer_pool.py`.
- Extended `RendererAdapterError` with `retryable`, `renderer_code`, and `renderer_category` fields.
- Updated pool retry behavior so typed non-retryable renderer failures fail fast, while typed retryable internal failures still replace the worker and retry within `max_retries`.

## Verification

- `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/worker-protocol-v2.test.ts __tests__/core-renderer-kernel.test.ts` passed: 14 tests.
- `uv run pytest services/gateway/tests/test_render_pool.py services/gateway/tests/test_render_failclosed.py -q` passed: 8 tests.
- `pnpm --filter @oh-my-class/renderer build` passed.
- `lsp_diagnostics` reported no diagnostics for `packages/renderer/src/agent-worker.ts`, `packages/renderer/__tests__/worker-protocol-v2.test.ts`, `services/gateway/renderer_pool.py`, `services/gateway/renderer_models.py`, `services/gateway/tests/test_render_pool.py`, and `services/gateway/tests/test_render_failclosed.py`.
- Manual stdin/stdout worker surface check passed by piping a V2 `fixture.echo` request to `node packages/renderer/dist/agent-renderer.js --worker`; observed `{ ok: true, html, manifest, diagnostics, metrics }` with `manifest.kind = "fixture.echo"`.

Note: timeout coverage is retained in `services/gateway/tests/test_renderer_adapter.py` and pool failure retry coverage is in `services/gateway/tests/test_render_failclosed.py`.
