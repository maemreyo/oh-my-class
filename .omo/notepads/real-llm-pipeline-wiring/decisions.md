
## Per-Artifact LLM Calls vs Batch (2026-06-27)

**Decision**: Each artifact type gets its own LLM call instead of one batch call.

**Rationale**: With 4omc reasoning model, combined output (~30K chars) exceeds max_tokens (24K→32K with reasoning overhead). Single-artifact calls keep each response within token budget.

**Trade-offs**:
- More LLM calls (N calls for N artifacts vs 1 call)
- But each call is smaller, faster, less likely to truncate
- Failure is isolated per artifact type (one failure doesn't waste all others)
- Retry scope is narrower (retry only the failed type)
- Return shape `{"artifacts": [...]}` preserved for downstream compatibility
