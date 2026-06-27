# Task 3: Gateway-to-Eta Renderer Adapter — Evidence

**Date**: 2026-06-27
**Status**: DONE

---

## Deliverables

| File | LOC (pure) | Purpose |
|------|-----------|---------|
| `services/gateway/renderer_adapter.py` | 130 | Python async adapter: spawns TS renderer subprocess, pipes JSON stdin, reads HTML stdout |
| `services/gateway/tests/test_renderer_adapter.py` | 121 | 13 tests covering success, errors, timeout, standalone HTML validation |
| `packages/renderer/package.json` | +3 lines | Added `"bin"` entry for `omc-render` CLI |

## Test Results

```
services/gateway/tests/test_renderer_adapter.py — 13/13 passed (0.71s)
packages/renderer/__tests__/* — 230/230 passed (1.31s)
```

## Test Matrix

| Test | Scenario | Expected | Actual |
|------|----------|----------|--------|
| `test_returns_html_on_exit_zero` | Mock renderer exits 0 + valid HTML | HTML string returned | PASS |
| `test_passes_json_via_stdin` | Mock reads JSON, echoes title | Title present in output | PASS |
| `test_raises_error_on_nonzero_exit` | Mock exits with code 1 | `RendererAdapterError` with "exit code 1" | PASS |
| `test_error_carries_exit_code` | Non-zero exit | `exit_code == 1` on error | PASS |
| `test_error_code_is_pipeline_error` | Non-zero exit | `error_code == "PIPELINE_ERROR"` | PASS |
| `test_raises_error_on_non_html_output` | Mock outputs "not html at all" | Error with "invalid output" | PASS |
| `test_raises_error_on_timeout` | Mock sleeps 999s, timeout 0.5s | Error with "timed out" | PASS |
| `test_timeout_default_is_30s` | Default RendererConfig | `timeout_seconds == 30.0` | PASS |
| `test_rejects_output_with_cdn_references` | Mock outputs CDN link | Error with "external assets" | PASS |
| `test_accepts_standalone_html` | Clean HTML | No error, no "cdn"/"https://" in output | PASS |
| `test_default_command` | Default RendererConfig | command contains "agent-renderer" | PASS |
| `test_custom_command` | Custom command override | Command and timeout match | PASS |
| `test_frozen_dataclass` | Attribute assignment | `AttributeError` raised | PASS |

## Manual QA Probes

| Probe | Input | Result |
|-------|-------|--------|
| success (mock HTML) | Valid standalone HTML mock | OK — 52 chars, DOCTYPE present |
| nonzero exit 2 | `exit(2)` | ERR — PIPELINE_ERROR, exit=2 |
| malformed output | "not html at all" | ERR — missing DOCTYPE detected |
| timeout (0.3s) | `sleep 999` | ERR — timed out after 0.3s |
| dirty CDN output | CDN link in HTML | ERR — external assets detected |
| empty stdout | No output | ERR — empty output detected |
| whitespace stdout | Whitespace only | ERR — caught as failure |
| missing binary | `/nonexistent/binary` | ERR — process start failure |

## Architecture Compliance

- **Package boundary respected**: Gateway adapter shells out to TS renderer via subprocess. No Python imports from `packages/renderer`.
- **No Eta duplication**: All rendering delegated to TypeScript. Python only serializes JSON and validates output.
- **No legacy `renderArtifactSync`**: Adapter invokes `agent-renderer.ts` which uses the async `renderAgentArtifact()`.
- **Process contract**: exit 0 + stdout HTML = success; non-zero/timeout/invalid = `RendererAdapterError` (subclass of `OMCError`).
- **Config-driven**: Command and timeout fully configurable. Defaults target compiled `dist/agent-renderer.js`.
- **No snapshot persistence**: Adapter returns HTML string. Snapshot store wiring is task 4.

## Edge Cases Probed

1. **Dirty worktree** (missing binary): Graceful `RendererAdapterError` with OS error message.
2. **Misleading output** (non-HTML garbage): Caught by standalone HTML validation — missing DOCTYPE.
3. **Hung process** (infinite sleep): Killed after timeout, clean error raised.
4. **Binary garbage** (null bytes in args): Caught by `ValueError` handler in process creation.

## DoneClaim

```json
{
  "task": 3,
  "title": "Gateway-to-Eta renderer adapter for artifact snapshots",
  "status": "done",
  "files_changed": [
    "services/gateway/renderer_adapter.py",
    "services/gateway/tests/test_renderer_adapter.py",
    "packages/renderer/package.json"
  ],
  "tests": {
    "adapter": "13/13 passed",
    "renderer_suite": "230/230 passed"
  },
  "invariants_held": [
    "INVARIANT-04: Output validated for no external assets",
    "INVARIANT-09: Theme rendering delegated to TS (theme.json is SSOT)",
    "Package boundary: services/gateway does not import from packages/renderer"
  ],
  "not_done": [
    "Snapshot persistence wiring (task 4)",
    "Integration with pipeline_v2_worker (task 4)"
  ]
}
```
