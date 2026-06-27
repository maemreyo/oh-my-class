# ADR-003: RunContract and Conditional Human-in-the-Loop

## Status

**Decided** (2026-06-27) — Pipeline V2 uses a persisted RunContract with append-only revisions and conditional HITL gates.

## Context

The current preflight only validates that `raw_request` exists and is long enough. Quickstart only sets a few defaults. This lets incomplete or ambiguous requests reach expensive LLM steps and fail minutes later. Diagnostic behavior is also unclear because the diagnostician silently skips when no student evidence is present.

Pipeline V2 needs a smart harness that asks teachers only when needed, but does not let downstream agents hallucinate missing scope.

## Decision

Introduce a `RunContract` resolved during setup.

The default mode is `generate_pack`. The `diagnose_then_generate` mode only runs when student evidence is provided, such as responses, quiz history, misconception notes, or uploaded work samples.

Preflight becomes a smart runnable-contract hard gate:

- deterministic validation first;
- infer safe defaults only when unambiguous;
- fail or clarify before LLM calls if required fields are missing;
- do not perform pedagogical planning.

Quickstart creates the immutable execution envelope:

- run id, thread id, timestamps;
- mode, grade, subject, language, locale, curriculum, artifact types, export formats;
- research policy and resolved budget;
- streaming policy;
- healing limits;
- quality thresholds;
- artifact generation parallelism;
- safety and Langfuse capture policy;
- config version/hash.

The contract uses append-only revisions:

- `current` points to the active revision;
- `revisions[]` records source, changes, reason, approval status, and effective stage;
- downstream steps cannot silently mutate contract values;
- high-risk changes require human approval;
- low-risk runtime adaptations can be auto-approved and logged.

Conditional gates:

- `clarification_required` when critical information is missing;
- `contract_confirmation` when risky defaults or important inferences need teacher confirmation;
- normal blueprint/content gates remain later in the flow.

## Consequences

- Teachers are not asked unnecessary questions.
- Expensive downstream work starts only after the request is runnable.
- Contract changes are auditable and reproducible.
- Downstream business logic reads the resolved RunContract, not raw `.env` or YAML.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Keep light preflight | Simple | Wastes LLM time and produces unclear failures |
| Ask teacher to confirm every default | Safe | Poor UX and too many interruptions |
| Mutable contract | Flexible | Hard to audit and debug |
| Append-only contract revisions | Flexible and auditable | Requires more persistence and UI support |
