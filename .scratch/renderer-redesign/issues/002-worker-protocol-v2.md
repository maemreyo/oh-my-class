---
title: Renderer worker protocol V2 with typed responses
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Upgrade the Python↔Node renderer boundary to send `WorkerRenderRequest` payloads and receive typed success/failure responses from the new renderer kernel. Keep stdin/stdout transport, but include `requestId`, `kind`, `input`, `context`, manifest, diagnostics, metrics, and typed retryable errors.

## Acceptance criteria

- [ ] Node worker accepts `{ requestId, kind, input, context }` and calls the new `render()` API.
- [ ] Successful worker responses include `{ ok: true, html, manifest, diagnostics, metrics }`.
- [ ] Failure responses include typed error `code`, `category`, `retryable`, `message`, and optional details.
- [ ] Python pool honors `retryable` and does not retry validation, unknown-kind, unsupported-audience, asset-policy, sanitizer, or template-not-found errors.
- [ ] Contract tests cover valid render, malformed JSON, version mismatch, unknown kind, validation error, retryable internal error, and timeout.

## Blocked by

- 000-capture-current-renderer-golden-baselines.md
- 001-core-renderer-kernel.md
