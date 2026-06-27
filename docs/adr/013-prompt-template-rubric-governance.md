# ADR-013: Prompt, Template, and Rubric Governance

## Status

**Decided** (2026-06-27) — Pipeline V2 treats prompts, templates, themes, and rubrics as versioned production modules with tests, evals, metadata, and governance.

## Context

Live failures showed that prompt quality and output contract consistency are production-critical. The current Content Creator prompt is long, hard to test, and can conflict with parser expectations. V2 also relies on rendered HTML snapshots and adaptive quality rubrics, so template and rubric changes need the same discipline as code changes.

## Decision

Prompt modules:

- Use a typed `PromptModule` registry.
- Prompt bodies are Markdown for human review.
- Code metadata/renderers define id, version, purpose, input contract, output contract, budget, schema strategy, safety policy, eval fixtures, owner stage, and changelog.
- Every prompt body change requires manual version bump and content hash validation.
- Startup/tests fail or hard-warn on version/hash drift.

Prompt compiler:

- Prompts are composed from sections with ids, priorities, include conditions, budgets, and compaction policy.
- Safe sections can be auto-compacted.
- Core contract/safety sections cannot be dropped or unsafe-truncated.
- If core sections overflow budget, fail before sending unsafe prompt.

Structured output:

- Use configurable structured output strategy per model/task: native schema, JSON object, prompt JSON, or text extraction.
- Prefer provider-native schema where live compatibility proves reliable.
- Always validate with canonical contracts.
- Repair is scoped and failure-type-specific.

Prompt eval:

- Prompt body changes for Planner, Research, Artifact, Healing, and Judge prompts require targeted live 9Router eval.
- Metadata-only changes require static tests.
- Regression corpus includes Math fractions, English phrasal verbs, Science citations, ambiguous clarification, and diagnosis evidence.

Localization and overlays:

- Use base prompts plus locale, curriculum, subject, and artifact overlays.
- Overlays have their own fixtures and combined evals.

Repair prompts:

- Use dedicated repair prompts by failure type.
- Repairs are scoped by default and cannot change unrelated content unless the failure classifier routes to broader regeneration.

Prompt observability:

- Persist compact prompt metadata in Postgres events.
- Send richer metadata to Langfuse.
- Production does not capture full prompts/outputs by default.

Tool boundaries:

- Prompts consume explicit inputs.
- Content Creator is not tool-enabled initially.
- Research Engine owns search/fetch.

Template and theme governance:

- Template/theme changes require manual version bump, hash validation, render tests, and changelog.
- Rendered snapshots store renderer, template, theme versions and hashes.

Rubric governance:

- Quality rubrics are versioned modules with deterministic and LLM criteria.
- Rubric compiler composes criteria from artifact type, subject, locale, curriculum, risk, and RunContract policy.

## Consequences

- Prompt/template/rubric changes become reviewable and testable production changes.
- Output contract drift is caught earlier.
- Live 9Router behavior is evaluated at prompt-module level, not only full pipeline level.
- Reproducibility improves through version and hash metadata.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Free-form prompt files | Easy editing | Weak contracts and eval discipline |
| Prompt strings in code | Type proximity | Harder human review and reuse |
| One universal prompt | Simple | Poor locale/subject adaptation |
| No template/rubric governance | Less process | Approval/export quality can drift invisibly |
