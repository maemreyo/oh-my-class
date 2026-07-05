# ADR-036: Component Strategy Knowledge and Governance

## Status

**Proposed** (2026-07-05) — Govern the Component Strategist's pedagogy knowledge, runtime index, reproducibility, observability, fallback, and feedback loops. Complements ADR-035.

## Context

A smart component selector needs more than a prompt. It needs an auditable knowledge base that says which learning moves and components fit which educational contexts, and a reproducible selector that can explain why it chose one option over another. The system must remain standalone/offline-safe, testable, and compatible with K-12 privacy/compliance constraints.

The tempting shortcut is a CSV or free-form model memory. That is insufficient: component intelligence is nested and relational. A single entry needs learning moves, component affordances, supported artifacts, Bloom/MOET fit, UDL tags, duration bounds, contraindications, fallback components, evidence sources, teacher rationale templates, and golden scenarios.

## Decision

1. **Source of truth = PR-reviewed YAML.** Pedagogy/component knowledge lives in repo YAML under a dedicated component-strategy knowledge directory. YAML is human-reviewable, versionable, comment-friendly, and supports nested metadata.
2. **Runtime search = generated SQLite index.** A build step validates YAML and generates a SQLite index for fast local query/search. SQLite is derived, reproducible, and never manually edited.
3. **Build-time generation, read-only runtime.** Generated SQLite is built in CI/package creation, included in the deployable artifact, and loaded read-only at runtime. Runtime never silently regenerates stale knowledge. CI fails if generated output is stale relative to YAML/manifests.
4. **Global manifest plus per-entry versions.** The knowledge DB has a global `knowledge_db_version`, manifest checksum, compatible schema/selector versions, and per-entry semantic versions. Snapshots store the manifest/checksum and exact selected knowledge refs.
5. **Knowledge lifecycle is explicit.** Entries are `production`, `draft`, or `deprecated`. Draft entries are loadable only in explicit non-production mode. Deprecated entries are replay-resolvable for old snapshots but not selectable for new runs or revisions, and they carry retention/removal metadata.
6. **Mutable runtime memory is separate.** Teacher preferences, component effectiveness, and later outcome signals live in existing store namespaces/adapters. They apply bounded multipliers and cannot redefine evidence, renderability, or compliance.
7. **LearningMove/Affordance ontology.** Knowledge is organized around `LearningMove`, `ComponentAffordance`, first-class negative rules/contraindications, and many-to-many component bindings with move-specific requirements. Renderer components are implementation leaves, not the organizing ontology.
8. **Rule conflicts are build-time failures unless explicit.** Intentional precedence requires priority, override, mutual-exclusion, or scoped applicability. Accidental conflict or YAML-order-dependent behavior fails validation.
9. **Renderer/exporter capability manifests.** The selector depends on generated capability metadata owned by renderer/exporter packages, not Eta templates, CSS classes, dispatcher internals, or export implementation details. Manifests are hybrid: mechanical support facts are generated; pedagogical/render-quality annotations are reviewed data.
10. **Typed research signals.** Research informs strategy through validated `ResearchSignals` such as misconception likelihood, concept difficulty, vocabulary load, factual risk, source confidence, prerequisite risk, and real-world-context viability. Raw research prose never enters selector scoring directly.
11. **Immutable strategy snapshots and append-only revisions.** Every run stores the exact finalized `ComponentStrategyPlan` used, including `strategy_schema_version`, `knowledge_db_version`, `selector_version`, `scoring_profile_id`, input fingerprint, selected move/component IDs, objective coverage, sequence/projection data, budgets, candidate score breakdowns, rejection reasons, applied multipliers, and fallback reason if any. Teacher feedback, content-fill failure, or quality recovery creates a new revision with parent lineage; snapshots are never mutated in place.
12. **Privacy-preserving fingerprints.** Cache keys, snapshots, and observability use normalized structured inputs only: objectives, context tags, versions, artifact/export requirements, locale, and typed signal digests. They do not include raw teacher text, free-form feedback, student names, emails, or individual student data.
13. **Compact snapshot plus optional TTL ledger.** Run state stores the compact approved plan and top rejection/fallback data needed for explanation and reproduction. Full debug ledgers are explicit diagnostic artifacts with PII redaction and TTL; they are not normal long-lived run state.
14. **Fail closed vs graceful fallback.** Invalid YAML, missing/unloadable SQLite index, version mismatch, unsupported component type, non-renderable selected component, compliance-unsafe component, missing reproducibility fields, or no valid component path fail closed. Missing teacher history, missing student outcomes, LLM rationale failure, or unavailable strategy variants degrade to deterministic `evidence_balanced_basic` with an explicit teacher/log note.
15. **Typed teacher feedback.** Teacher actions become typed events such as `switch_variant`, `increase_style`, `decrease_style`, `prefer_component_family`, `reject_component_family`, and bounded `reject_reason` values. Feedback recomputes within the valid candidate universe, creates an append-only revision, and informs future runs as layered bounded soft multipliers with precedence and decay.
16. **Quality score and golden scenarios.** The strategy layer exposes a deterministic `StrategyQualityScore` covering objective alignment, evidence-signal coverage, component diversity, Bloom/MOET progression, Gagne coverage, retrieval/formative presence, repetition penalty, unsupported/prose-only penalty, readiness, budget fit, accessibility/differentiation intent, export projection status, and compliance safety. Golden scenarios assert focused pedagogical expectations instead of brittle whole-plan snapshots.
17. **Data-first extensibility.** Adding a renderable component binding, strategy family, domain/language overlay, scoring profile, or declarative validator should require YAML + tests, not selector-code changes. Adding a brand-new component type still requires Pydantic/TypeScript contracts, renderer dispatcher/plugin support, capability manifest update, and render tests.
18. **Offline-safe media policy.** Media-like moves are allowed only as text/reference metadata or locally generated inline assets. External embeds, CDN assets, `http(s)` image/script/link/font dependencies, student PII, and teacher-only fields on student surfaces are hard-filtered.

## Consequences

- Strategy decisions are explainable, diffable, reproducible, and debuggable.
- Repo knowledge grows under normal code-review/CI discipline instead of runtime drift.
- SQLite gives runtime performance without making the database the source of truth.
- The system can learn teacher preference over time without learning bad pedagogy as a hard rule.
- Authoring new strategy knowledge requires CI/schema/render/evidence checks, which raises the bar but prevents silent degradation.
- Strategy decisions remain reproducible across YAML, scoring, renderer capability, and feedback changes because finalized plans are immutable and revisions are append-only.
- The selector can adapt to language/domain overlays and future outcome signals without forking the core engine.

## Alternatives Considered

| Option | Pros | Cons |
|---|---|---|
| YAML source + generated SQLite index (chosen) | Reviewable and fast; supports nested evidence; reproducible | Requires generator and validation CI |
| CSV source | Simple | Too flat for nested pedagogy/evidence/contraindications/fallbacks |
| Runtime database as source of truth | Editable in app | Non-reproducible, hard to review, risky for pedagogy drift |
| LLM memory/vector store as source | Flexible semantic recall | Weak determinism and auditability; cannot be sole authority |
| Teacher preference as primary signal | Personalizes quickly | Can reinforce boring or pedagogically weak habits |

## References

- ADR-012 data governance and versioning
- ADR-013 prompt/template/rubric governance
- ADR-019 learning-outcome effectiveness loop
- ADR-025 renderer artifact-kind plugin registry
- ADR-032 verification integrity and engineering discipline
- ADR-033 specialized module standard
- ADR-035 component strategist stage
- ADR-037 component strategy fallback and feedback conflicts
- ADR-038 component strategy validators and release gates
- `.scratch/component-strategist/README.md`
