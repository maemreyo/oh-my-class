---
title: "Import-linter contract: forbid openai/litellm imports outside packages.llm_client"
status: ready-for-agent
labels: [governance, import-linter, llm]
created: 2026-07-08
priority: p1
epic: llm-governance-hardening
sequence: 1
---

> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 1.

## What to build

As of 2026-07-08, only two non-`packages.llm_client` files import `openai`:
1. `packages/agents/llm/chat.py:6` — `from openai import OpenAIError`, used only to catch the SDK's exception type; already routes calls through `LLMClient`.
2. `packages/agents/llm/transport.py:27` — `complete_non_streaming_chat(client: AsyncOpenAI, ...)` calls `client.chat.completions.create()` directly, but has **zero callers anywhere** (dead code).

Before adding the contract:
1. Delete `complete_non_streaming_chat` and its now-unused `AsyncOpenAI`/`ChatCompletionMessageParam` TYPE_CHECKING imports from `transport.py`.
2. Move `OpenAIError` (or an equivalent exception re-export) into `packages/llm_client`, and update `chat.py` to import it from there instead of directly from `openai`.

Then add an `import-linter` contract to `pyproject.toml` (alongside the existing `packages-no-import-services`/`common-is-the-floor`/`layered-architecture` contracts):

```toml
[[tool.importlinter.contracts]]
name = "no-direct-llm-sdk-imports"
type = "forbidden"
source_modules = ["packages", "services", "common"]
forbidden_modules = ["openai", "litellm"]
# packages.llm_client itself is the only legitimate importer — import-linter's
# forbidden-contract source_modules should exclude it; consult import-linter
# docs for the current syntax (ignore_imports or a narrower source_modules list).
```

Note: this contract intentionally does **not** cover `httpx` — see `LGH-02` for why that needs a different mechanism.

## Acceptance criteria

- [ ] `complete_non_streaming_chat` deleted from `transport.py`; no other dead code left behind in that file.
- [ ] `chat.py` no longer imports `openai` directly.
- [ ] New import-linter contract added to `pyproject.toml`; `lint-imports` passes with zero exceptions/ignores needed.
- [ ] CI's existing `lint-imports-python` job (`.github/workflows/ci.yml:21-30`) catches a regression if someone reintroduces a direct `openai`/`litellm` import outside `packages/llm_client`.

## Blocked by

Nothing.
