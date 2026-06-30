# Runbook: Render Pool Crash

## Symptom

- Teaching pack export fails with `RendererAdapterError` or `ExportError`.
- Log lines contain "Renderer worker pipe failed", "Renderer worker exited before responding",
  or "Failed to start renderer worker".
- HTML export files are not produced; artifact snapshot render step stalls.
- Render requests return 5xx from the gateway's export endpoint.

## Alert

SLO breach may fire on `success_rate` (`global:success_rate`) if enough export-backed
runs fail. Alert delivered via `dispatch_slo_alerts` in `services/gateway/slo_alerting.py`.

## Diagnosis

1. Check gateway logs for `RendererAdapterError` with details:
   - `"Renderer worker pipe failed"` — worker process lost its stdin/stdout pipe (crashed).
   - `"Renderer worker timed out after Ns"` — worker hung; check Node.js renderer process.
   - `"Renderer worker exited before responding"` — worker exited unexpectedly; check stderr.
   - `"Failed to start renderer worker"` — renderer binary missing or misconfigured.
2. Inspect `RendererConfig` in use: confirm `command`, `pool_size`, `max_retries`, and
   `timeout_seconds` are correct (set via env vars or defaults in `renderer_models.py`).
3. Check how many workers are in the pool and whether they are alive:
   - Pool lives in `services/gateway/renderer_pool.py` — `_POOLS` module-level dict.
   - Each `RendererPool` holds `_workers: list[RendererWorker]`; workers with
     `process.returncode is not None` have exited.
4. Confirm the Node.js renderer binary is present and executable:
   ```
   ls -la <renderer_command_path>
   node --version
   ```
5. Run the renderer manually to reproduce the error:
   ```
   echo '{"renderer_version":"...","template_version":"...","artifact":{}}' | node <renderer> --worker
   ```

## Remediation

1. **Automatic path**: `RendererPool.render` retries up to `max_retries` times, calling
   `_replace_worker` on each failure — the crashed worker is terminated via
   `terminate_worker` (SIGKILL + wait) and a fresh one is started via `start_worker`.
   If retries are exhausted, `RendererAdapterError` is raised to the caller.

2. **Full pool reset** (clears all cached pools and forces fresh workers on next render):
   ```python
   # In a gateway admin script or REPL:
   from services.gateway.renderer_pool import close_renderer_pools
   import asyncio
   asyncio.run(close_renderer_pools())
   ```
   Or restart the gateway process, which clears the module-level `_POOLS` dict.

3. **If renderer binary is missing or broken**: redeploy the renderer package:
   ```
   cd packages/renderer && npm ci && npm run build
   ```
   Then restart the gateway.

4. **If pool_size or timeout is mis-configured**: update the relevant env vars
   (`OMC_RENDERER_POOL_SIZE`, `OMC_RENDERER_TIMEOUT_SECONDS`) and restart.

## Escalation

- If fresh workers consistently crash on startup, escalate to the renderer team with
  the stderr output from a manual invocation.
- If the crash is reproducible with a specific artifact payload, file a bug with the
  artifact JSON and renderer version.
- If export is blocking a classroom session, temporarily disable render-backed exports
  and serve raw JSON snapshots until the renderer is restored.

## Verify

1. Trigger a test render via the export endpoint and confirm HTML is produced:
   ```
   POST /teaching-packs/runs/{run_id}/export
   ```
   Expect: 200 with exported file paths.
2. Confirm no `RendererAdapterError` lines appear in the gateway log.
3. Check `close_renderer_pools` is not needed — fresh pool should auto-start on next
   render request if the previous one was cleared.
