# ADR-010: Teaching Pack Testing and Observability

## Status

**Decided** (2026-06-27) — Teaching Pack requires real production-path integration tests, live 9Router validation, persisted events, and Langfuse trace correlation.

## Context

The current automated tests pass, but live full-flow runs fail after teacher approval. This proves that mocked/unit-level confidence is not enough for production behavior. Teaching Pack must validate real orchestration, persistence, web search/fetch, LLM behavior, rendering, gates, SSE, and export.

## Decision

Use a layered test strategy.

Unit tests:

- fakes/mocks are allowed for deterministic logic;
- test contracts, policies, status transitions, source ranking, safety gates, streaming policy, and healing classifiers.

Integration tests:

- real Postgres;
- real LangGraph Postgres checkpointer;
- real run store;
- real artifact snapshot store;
- real gateway/executor integration;
- SSE replay from persisted events.

Live 9Router validation:

- targeted live smoke tests for issues touching LLM/Search/Generation/Gates;
- full live Teaching Pack release matrix before claiming production readiness;
- live evidence is required for production behavior claims.

Keep deterministic E2E tests as regression guards, but do not treat them as production proof.

Required release scenarios include:

- Vietnamese Grade 5 Math equivalent fractions;
- English Grade 7 travel phrasal verbs;
- Science factual/citation scenario;
- missing grade/subject clarification;
- contract confirmation;
- search plan confirmation;
- scoped artifact rejection/healing;
- standalone HTML export;
- 9Router timeout/adaptive streaming fallback;
- Langfuse unavailable but pipeline continues.

Observability:

- Postgres event log is canonical for progress and audit;
- Langfuse is trace mirror only;
- trace metadata includes run id, stage, step, artifact id, contract revision id, gate, research plan id, model, transport, attempt, and streaming policy;
- default Langfuse IO capture stores summaries/hashes, not full prompts/outputs.

CI/release gates:

- Python lint/tests;
- TypeScript tests/typecheck;
- import/dependency boundaries;
- Alembic migration validation;
- real Postgres integration subset;
- deterministic E2E;
- live 9Router release validation before production cutover.

## Consequences

- Teaching Pack cannot be called production-ready based only on unit tests.
- Live provider behavior is continuously exercised where it matters.
- Observability remains privacy-conscious and correlated with product state.
- Developers still have fast deterministic feedback loops.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Mocked tests only | Fast and stable | Misses real provider timeout/malformed output behavior |
| Live tests only | Realistic | Slow/flaky and poor for local regression |
| Store all prompts/outputs in Langfuse | Easier debugging | Privacy and size risks |
| Deterministic regression + live production proof | Balanced | Requires maintaining two suites |
