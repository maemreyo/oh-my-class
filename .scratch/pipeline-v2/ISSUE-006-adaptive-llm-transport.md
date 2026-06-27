---
title: Pipeline V2 adaptive LLM transport and Langfuse metadata policy
status: ready-for-agent
labels: [pipeline-v2, llm, streaming, langfuse, 9router]
created: 2026-06-27
order: 6
blocked_by: [ISSUE-001-foundation-architecture, ISSUE-004-run-contract-setup-stage]
adr_refs:
  - docs/adr/007-adaptive-llm-transport.md
  - docs/adr/010-pipeline-v2-testing-and-observability.md
---

## Problem

Hard-coded streaming for one agent is not enough. Researcher can still timeout, and strict JSON generation can still fail after streaming. V2 needs configurable transport policy that uses live 9Router behavior safely.

## Scope

Implement adaptive LLM transport policy for Pipeline V2.

Agent-ready tasks:

1. Add transport policy contract and implementation.
2. Use RunContract snapshot for thresholds, modes, retries, and capture policy.
3. Decide streaming/non-streaming per task using agent, task, message chars, max tokens, attempt, previous error, strict JSON, and artifact context.
4. Add timeout-to-stream fallback for safe tasks.
5. Add strict JSON strategy hooks for bounded generation and extraction.
6. Ensure live 9Router calls include correct metadata tags.
7. Standardize Langfuse summaries/hashes by default and full IO dev-only opt-in.
8. Add privacy pre-LLM gate before sending prompts.

## Out Of Scope

- Refactoring every V1 LLM call.
- Artifact-level generation implementation.
- Research Engine search/fetch logic.

## Acceptance Criteria

- Long artifact generation and large research synthesis choose streaming by policy.
- Short judge/classification tasks remain non-streaming by default.
- A 504/function timeout can retry with streaming where safe.
- Langfuse does not capture full prompts/outputs when disabled.
- Prompt/output hashes and lengths are recorded.
- Policy decisions are testable and visible in events/traces.

## Test Plan

- Unit tests for transport policy decisions.
- Live 9Router smoke for a long generation task that streams.
- Live 9Router smoke for a short non-streaming task.
- Langfuse metadata tests with full IO disabled.
- Privacy tests for pre-LLM gate.

## Observability

- Emit compact events for LLM call started/completed/failed with transport, reason, duration, attempt, and error type.
- Trace metadata includes run id, stage, task, artifact id, model, transport, streaming policy reason, attempt, and prompt/output hashes.

## Required Edge Cases And Tests

- Policy chooses streaming for long artifact generation and large research synthesis.
- Policy keeps short judge/classification calls non-streaming unless retry rules require streaming.
- Timeout/function invocation timeout retries with streaming only for safe idempotent units.
- Streaming task with empty content, partial JSON, multiple JSON objects, or prose-wrapped JSON returns structured error classes.
- Native schema mode, JSON-object mode, prompt-JSON mode, and text-extract mode are selected by config and model capability.
- Prompt/output full IO is not captured when disabled, even on error.
- Langfuse down does not fail the LLM call.
- Prompt size overflow triggers compiler compaction or hard fail before sending request.
- Idempotency prevents repeating an already persisted valid artifact output after worker retry.
- Live 9Router tests cover a long streamed call, a short non-streamed call, and timeout-to-stream fallback if reproducible.

## Rollback

If adaptive policy causes regressions, set config to conservative mode while preserving the V2 transport interface.
