# ADR-007: Adaptive LLM Transport

## Status

**Decided** (2026-06-27) — Pipeline V2 uses configurable per-task adaptive streaming rather than global streaming or hard-coded agent streaming.

## Context

Live full-flow testing showed Content Creator non-streaming calls timed out. Enabling streaming for Content Creator avoided the transport timeout, but generation still failed with malformed or empty JSON. Researcher still hit non-streaming 504 timeouts on large prompts. The root issue is both transport policy and oversized generation units.

Pipeline V2 must use 9Router live behavior as a production validation target.

## Decision

Introduce a `StreamingPolicy` or `LLMTransportPolicy` module.

Policy input:

- agent;
- task;
- message chars;
- max tokens;
- attempt number;
- previous error type;
- expected output size;
- requires strict JSON;
- artifact id/type when relevant;
- RunContract config.

Policy output:

- `transport`: `non_streaming` or `streaming`;
- reason;
- JSON strategy;
- retry/fallback strategy;
- tracing metadata.

Rules:

- Stream long generation tasks such as artifact generation, research synthesis with large prompts, long-form healing, and export/content generation.
- Keep short classification, judge, schema repair, and small summarization non-streaming by default.
- If non-streaming fails with timeout or function invocation timeout, retry with streaming when safe.
- If prompt size or max tokens exceed thresholds, stream on first attempt.
- Strict JSON streaming must use bounded generation, extraction, and smaller units rather than blindly parsing a huge streamed buffer.

Content generation is split by artifact. Streaming is not a substitute for smaller generation units.

Langfuse captures summaries/hashes by default:

- full prompt/output capture is disabled by default;
- full IO is dev-only opt-in;
- production traces store message counts, chars, hashes, duration, model, transport, usage when available, and error type.

## Consequences

- Transport behavior is explainable, configurable, and testable.
- Long calls avoid provider timeout where possible.
- Short calls preserve usage metadata and simplicity.
- Strict JSON reliability is addressed through unit sizing and validation, not streaming alone.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Stream everything | Avoids some timeouts | Loses usage metadata; partial output risk; unnecessary for small tasks |
| Only Content Creator streams | Minimal change | Researcher and healing can still timeout |
| Per-task adaptive transport | Balanced and production-ready | Requires policy module and tests |
