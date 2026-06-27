# ADR-009: Quality, Healing, and Safety Gates

## Status

**Decided** (2026-06-27) — Pipeline V2 uses per-artifact deterministic gates, adaptive LLM judges, typed healing, and privacy/safety gates before search, LLM calls, and publish.

## Context

The current quality flow runs after whole-pack generation. A single malformed artifact can fail the whole pack, and healing routes back to pack-level generation. The product also handles teacher requests, possible student evidence, web search, LLM calls, answer keys, rendered HTML, and traces, so privacy and safety must be part of the core pipeline rather than final cleanup.

## Decision

Quality model:

- run deterministic gates per artifact;
- use adaptive artifact LLM judge only when risk, borderline score, rigorous mode, or artifact type requires it;
- run pack-level coherence review after required artifacts pass;
- do not reach teacher content approval until required artifacts meet minimum quality.

Per-artifact deterministic gates include:

- schema validation;
- placeholder/lorem checks;
- answer-key separation;
- language/age/readability checks;
- presentation contract after render;
- external asset scan;
- accessibility basics;
- unsupported component detection.

Pack-level review checks:

- objective alignment;
- vocabulary consistency;
- duplicate or conflicting instructions;
- assessment matches lesson;
- answer keys remain teacher-only;
- export readiness.

Healing model:

- classify failures into typed categories;
- automatically heal internal gate failures within limits;
- teacher HITL rejection is scoped by artifact/section and teacher-directed;
- contract-changing feedback creates a contract revision.

Healing strategies include:

- malformed JSON repair or smaller unit generation;
- schema repair;
- answer-key leakage repair;
- research enrichment for factual uncertainty;
- artifact regeneration for local mismatch;
- blueprint/contract routing for deeper mismatch;
- streaming or smaller units for timeout.

Safety/privacy gates:

- pre-search gate strips or blocks student PII in search queries;
- pre-LLM gate enforces metadata, capture policy, PII scan, and budget limits;
- pre-publish gate scans rendered artifacts for PII, answer-key leakage, external assets, and unsafe HTML.

Langfuse stores summaries/hashes by default. Full prompt/output capture is dev-only opt-in.

## Consequences

- Quality failures are local, explainable, and repairable.
- Teachers see clearer feedback and scoped rejection controls.
- Privacy is enforced before data leaves the system, not only at export.
- Artifact and pack quality can be tested independently.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Pack-level quality only | Simpler | Expensive retries and poor diagnostics |
| Judge every artifact always | High scrutiny | Slow and costly; unnecessary for low-risk artifacts |
| Final safety gate only | Easier | PII can already leak to search/LLM/traces |
| Per-artifact gates + adaptive judge + safety gates | Robust and scalable | More contracts and test cases |
