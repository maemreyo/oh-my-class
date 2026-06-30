---
title: Long-lived render worker pool + version pinning + concurrency cap
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Replace the per-render Node subprocess spawn with a reusable render backend. Today `services/gateway/renderer_adapter.py::render_artifact_content` does `asyncio.create_subprocess_exec` **per artifact render** (Node cold-start + Eta/DOMPurify/template load every time); with unit fan-out this multiplies into a process storm.

- **Render backend behind the existing `render(artifact) -> str` Protocol**: a **long-lived pool of N Node render workers** (persistent process with a stdin request-loop) or a render sidecar service, amortizing boot. Keep subprocess-per-render as a **dev fallback** (config), same Protocol — no caller change.
- **Version pinning**: the renderer validates input against the **generated Zod schema** (reuse the Pydantic→Zod codegen) and the adapter stamps + checks `renderer_version`/`template_version`; a contract change without a renderer rebuild **fails fast**, never mis-renders.
- **Concurrency + safety**: a semaphore caps concurrent renders (composed with worker concurrency from issue 001) to prevent process storms; bounded retry for transient subprocess failures; stderr captured into the trace; render failure stays **fail-closed** (never an empty pack).

## Acceptance criteria

- [ ] Rendering goes through a reusable backend (persistent pool/sidecar) behind the existing `render()` Protocol; subprocess-per-render remains a config-selectable dev fallback.
- [ ] Node/module boot is amortized across renders (measured: not a fresh process per artifact in pool mode).
- [ ] The renderer validates input against the generated Zod schema; a contract/renderer version mismatch fails fast with a clear error.
- [ ] Concurrent renders are bounded by a semaphore; no unbounded process spawn under fan-out.
- [ ] Transient subprocess failures retry (bounded); persistent failures are fail-closed with stderr in the trace.

## Detailed test suite

(Real renderer backend + real artifacts.)

- [ ] `services/gateway/tests/test_render_pool.py`: N renders reuse pool workers (process count stays bounded, not N spawns).
- [ ] `services/gateway/tests/test_render_version_pin.py`: an artifact that violates the generated Zod schema / a version mismatch fails fast (no mis-render).
- [ ] `services/gateway/tests/test_render_concurrency_cap.py`: a burst of renders never exceeds the configured concurrent-process cap.
- [ ] `services/gateway/tests/test_render_failclosed.py`: a renderer crash yields `RendererAdapterError` (no empty/partial HTML emitted), with stderr captured.
- [ ] Regression: `render_artifact_content` output is byte-identical between dev-subprocess and pool mode for a golden artifact.
- [ ] Run `uv run pytest services/gateway/tests/test_render_*.py -v`.

## Blocked by

None - can start immediately
