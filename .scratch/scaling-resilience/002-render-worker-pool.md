---
title: Long-lived render worker pool + version pinning + concurrency cap
status: done
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Replace the per-render Node subprocess spawn with a reusable render backend. Today `services/gateway/renderer_adapter.py::render_artifact_content` does `asyncio.create_subprocess_exec` **per artifact render** (Node cold-start + Eta/DOMPurify/template load every time); with unit fan-out this multiplies into a process storm.

- **Render backend behind the existing `render(artifact) -> str` Protocol**: a **long-lived pool of N Node render workers** (persistent process with a stdin request-loop) or a render sidecar service, amortizing boot. Keep subprocess-per-render as a **dev fallback** (config), same Protocol — no caller change.
- **Version pinning**: the renderer validates input against the **generated Zod schema** (reuse the Pydantic→Zod codegen) and the adapter stamps + checks `renderer_version`/`template_version`; a contract change without a renderer rebuild **fails fast**, never mis-renders.
- **Concurrency + safety**: a semaphore caps concurrent renders (composed with worker concurrency from issue 001) to prevent process storms; bounded retry for transient subprocess failures; stderr captured into the trace; render failure stays **fail-closed** (never an empty pack).

## Acceptance criteria

- [x] Rendering goes through a reusable backend (persistent pool/sidecar) behind the existing `render()` Protocol; subprocess-per-render remains a config-selectable dev fallback.
- [x] Node/module boot is amortized across renders (measured: not a fresh process per artifact in pool mode).
- [x] The renderer validates input against the generated Zod schema; a contract/renderer version mismatch fails fast with a clear error.
- [x] Concurrent renders are bounded by a semaphore; no unbounded process spawn under fan-out.
- [x] Transient subprocess failures retry (bounded); persistent failures are fail-closed with stderr in the trace.

## Detailed test suite

(Real renderer backend + real artifacts.)

- [x] `services/gateway/tests/test_render_pool.py`: N renders reuse pool workers (process count stays bounded, not N spawns); `TestRenderVersionPin` covers version mismatch and schema violation.
- [x] `services/gateway/tests/test_render_concurrency_cap.py`: a burst of renders never exceeds the configured concurrent-process cap.
- [x] `services/gateway/tests/test_render_failclosed.py`: a renderer crash yields `RendererAdapterError` (no empty/partial HTML emitted), with stderr captured.
- [x] Run `uv run pytest services/gateway/tests/test_render_pool.py services/gateway/tests/test_render_concurrency_cap.py services/gateway/tests/test_render_failclosed.py -v`.

## Verification

- `uv run pytest services/gateway/tests/test_render_pool.py services/gateway/tests/test_render_concurrency_cap.py services/gateway/tests/test_render_failclosed.py -q` → 9 passed.
- LSP diagnostics clean for `services/gateway/renderer_pool.py`, `services/gateway/renderer_models.py`, `services/gateway/renderer_adapter.py`.

## Blocked by

None - can start immediately
